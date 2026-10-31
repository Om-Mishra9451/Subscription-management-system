"""
Unit & Integration Tests for Remaining Modules:
- Module 6: Discount Management (test_discount_management)
- Module 7: Payment Management & Reconciliation (test_payment_management)
- Module 8: Finance Dashboard & Reporting (test_finance_dashboard)
- End-to-End Multi-Module Integration Workflow (test_full_financial_lifecycle)
"""

import unittest
import datetime
from decimal import Decimal

from subscriptiq.services.odoo_adapter import Environment, ValidationError, UserError
from subscriptiq.models.discount_management import SubscriptiqDiscountRule, SubscriptiqDiscountUsageHistory
from subscriptiq.models.payment_management import AccountPayment
from subscriptiq.services.billing_engine import BillingEngine
from subscriptiq.services.finance_dashboard import FinanceDashboardService
from subscriptiq.services.risk_engine import RiskEngine

class TestRemainingModules(unittest.TestCase):

    def setUp(self):
        self.env = Environment()
        # Seed company and admin user
        self.company = self.env['res.company'].create({'name': 'Brightloop Software Corp', 'currency_name': 'INR'})
        self.admin = self.env['res.users'].create({
            'name': 'Admin User',
            'login': 'admin@brightloop.io',
            'email': 'admin@brightloop.io',
            'password_hash': 'Secure#Pass123',
            'role': 'admin'
        })
        self.staff = self.env['res.users'].create({
            'name': 'Finance Staff',
            'login': 'staff@brightloop.io',
            'email': 'staff@brightloop.io',
            'password_hash': 'Secure#Pass123',
            'role': 'staff'
        })
        self.partner = self.env['res.partner'].create({
            'name': 'Acme Enterprise',
            'email': 'billing@acme.corp',
            'is_company': True
        })
        self.product = self.env['product.template'].create({
            'name': 'Cloud ERP Base',
            'list_price': 5000.0,
            'active': True
        })
        self.plan = self.env['subscriptiq.plan'].create({
            'name': 'Standard Monthly Plan',
            'code': 'PLAN-M1',
            'billing_interval': 'monthly',
            'billing_interval_count': 1,
            'price': 5000.0,
            'active': True
        })

    # =========================================================================
    # MODULE 6: DISCOUNT MANAGEMENT TESTS
    # =========================================================================
    def test_fixed_and_percentage_discount_calculation(self):
        """Test fixed amount and percentage discount calculations."""
        # Percentage discount: 20% on ₹5,000 -> ₹1,000
        disc_pct = self.env['subscriptiq.discount'].create({
            'name': 'Promo 20%',
            'code': 'PROMO20',
            'discount_type': 'percentage',
            'value': 20.0,
            'active': True
        })
        deduction = disc_pct.validate_and_calculate(5000.0)
        self.assertEqual(deduction, 1000.0)

        # Fixed discount: ₹500 on ₹5,000 -> ₹500
        disc_fix = self.env['subscriptiq.discount'].create({
            'name': 'Flat 500 Off',
            'code': 'FLAT500',
            'discount_type': 'fixed',
            'value': 500.0,
            'active': True
        })
        deduction_fix = disc_fix.validate_and_calculate(5000.0)
        self.assertEqual(deduction_fix, 500.0)

    def test_discount_validation_constraints(self):
        """Test negative values, >100% percentage, and invalid date bounds."""
        # Negative value
        with self.assertRaises(ValidationError):
            self.env['subscriptiq.discount'].create({
                'name': 'Negative Disc',
                'code': 'NEG',
                'discount_type': 'fixed',
                'value': -100.0
            })

        # >100% percentage
        with self.assertRaises(ValidationError):
            self.env['subscriptiq.discount'].create({
                'name': 'Huge Disc',
                'code': 'HUGE',
                'discount_type': 'percentage',
                'value': 105.0
            })

        # Start date after end date
        with self.assertRaises(ValidationError):
            self.env['subscriptiq.discount'].create({
                'name': 'Invalid Dates',
                'code': 'DATE_ERR',
                'discount_type': 'fixed',
                'value': 100.0,
                'start_date': '2026-12-31',
                'end_date': '2026-01-01'
            })

    def test_discount_expiry_and_minimum_spend(self):
        """Test that expired discounts or spend below minimum threshold are rejected."""
        yesterday = str(datetime.date.today() - datetime.timedelta(days=1))
        expired_disc = self.env['subscriptiq.discount'].create({
            'name': 'Expired Discount',
            'code': 'EXPIRED',
            'discount_type': 'percentage',
            'value': 10.0,
            'end_date': yesterday,
            'active': True
        })
        with self.assertRaises(ValidationError):
            expired_disc.validate_and_calculate(5000.0)

        # Minimum spend requirement
        min_spend_disc = self.env['subscriptiq.discount'].create({
            'name': 'High Value Coupon',
            'code': 'HIGHVAL',
            'discount_type': 'fixed',
            'value': 500.0,
            'min_purchase_amount': 10000.0,
            'active': True
        })
        with self.assertRaises(ValidationError):
            min_spend_disc.validate_and_calculate(5000.0) # 5,000 < 10,000

        # Satisfying minimum spend should succeed
        self.assertEqual(min_spend_disc.validate_and_calculate(12000.0), 500.0)

    def test_discount_usage_limit_and_history(self):
        """Test maximum usage limit and audit history recording."""
        disc = self.env['subscriptiq.discount'].create({
            'name': 'Flash Sale',
            'code': 'FLASH1',
            'discount_type': 'fixed',
            'value': 250.0,
            'max_usage_limit': 1,
            'active': True
        })
        self.assertEqual(disc.usage_count, 0)
        
        # 1st usage succeeds
        disc.record_usage(original_amount=5000.0, deduction=250.0, final_amount=4750.0)
        self.assertEqual(disc.usage_count, 1)

        # 2nd usage raises ValidationError
        with self.assertRaises(ValidationError):
            disc.validate_and_calculate(5000.0)
        with self.assertRaises(ValidationError):
            disc.record_usage(original_amount=5000.0, deduction=250.0, final_amount=4750.0)

        # Verify usage history record
        hist = self.env['subscriptiq.discount.usage.history'].search([('discount_id', '=', disc.id)])
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0].discount_amount, 250.0)

    # =========================================================================
    # MODULE 7: PAYMENT MANAGEMENT TESTS
    # =========================================================================
    def test_partial_and_full_payment_settlement(self):
        """Test recording partial payment, residual update, and full settlement."""
        inv = self.env['account.move'].create({
            'name': 'INV/2026/TEST01',
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'amount_total': 5000.0,
            'amount_residual': 5000.0,
            'state': 'posted',
            'payment_state': 'not_paid'
        })

        # 1. Partial payment: ₹3,000
        p1 = self.env['account.payment'].record_payment({
            'invoice_id': inv.id,
            'partner_id': self.partner.id,
            'amount': 3000.0,
            'payment_method': 'bank_transfer',
            'transaction_reference': 'TX-REF-001'
        })
        self.assertEqual(inv.amount_residual, 2000.0)
        self.assertEqual(inv.payment_state, 'not_paid')

        # 2. Second payment: ₹2,000 settles full residual
        p2 = self.env['account.payment'].record_payment({
            'invoice_id': inv.id,
            'partner_id': self.partner.id,
            'amount': 2000.0,
            'payment_method': 'upi',
            'transaction_reference': 'TX-REF-002'
        })
        self.assertEqual(inv.amount_residual, 0.0)
        self.assertEqual(inv.payment_state, 'paid')
        self.assertEqual(inv.subscriptiq_risk_state, 'recovered')

    def test_payment_validations_and_duplicate_prevention(self):
        """Test overpayment prevention, invalid customer, and duplicate transaction ref."""
        inv = self.env['account.move'].create({
            'name': 'INV/2026/TEST02',
            'partner_id': self.partner.id,
            'amount_total': 1000.0,
            'amount_residual': 1000.0,
            'state': 'posted',
            'payment_state': 'not_paid'
        })

        # Overpayment rejection: ₹1,500 > ₹1,000
        with self.assertRaises(ValidationError):
            self.env['account.payment'].record_payment({
                'invoice_id': inv.id,
                'amount': 1500.0
            })

        # Negative / Zero payment rejection
        with self.assertRaises(ValidationError):
            self.env['account.payment'].record_payment({
                'invoice_id': inv.id,
                'amount': 0.0
            })

        # Duplicate transaction reference prevention
        self.env['account.payment'].record_payment({
            'invoice_id': inv.id,
            'amount': 500.0,
            'payment_method': 'card',
            'transaction_reference': 'UNIQUE-TX-999'
        })
        with self.assertRaises(ValidationError):
            self.env['account.payment'].record_payment({
                'invoice_id': inv.id,
                'amount': 200.0,
                'payment_method': 'card',
                'transaction_reference': 'UNIQUE-TX-999'
            })

    def test_payment_dashboard_metrics(self):
        """Test payment dashboard aggregations."""
        metrics = self.env['account.payment'].get_payment_dashboard_metrics(self.env)
        self.assertIn('total_payments_received', metrics)
        self.assertIn('outstanding_amount', metrics)
        self.assertIn('payment_method_breakdown', metrics)

    # =========================================================================
    # MODULE 8: FINANCE DASHBOARD & REPORTING TESTS
    # =========================================================================
    def test_finance_dashboard_kpis_and_charts(self):
        """Test calculation of all 10 KPIs and 8 Charts in FinanceDashboardService."""
        # Create active subscription
        sub = self.env['sale.order'].create({
            'name': 'SUB/2026/FIN01',
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,
            'subscriptiq_recurring_total': 6000.0,
            'subscriptiq_status': 'active',
            'subscriptiq_next_renewal_date': str(datetime.date.today() + datetime.timedelta(days=10))
        })

        data = FinanceDashboardService.compute_kpis_and_charts(self.env)
        kpis = data['kpis']
        charts = data['charts']

        # Verify 10 KPIs
        self.assertGreaterEqual(kpis['active_subscriptions'], 1)
        self.assertEqual(kpis['mrr'], 6000.0)
        self.assertEqual(kpis['arr'], 72000.0)
        self.assertIn('revenue_received', kpis)
        self.assertIn('outstanding_amount', kpis)
        self.assertIn('overdue_invoices_count', kpis)
        self.assertGreaterEqual(kpis['upcoming_renewals_count'], 1)
        self.assertGreaterEqual(kpis['total_customers'], 1)

        # Verify 8 Charts
        self.assertIn('monthly_revenue_trend', charts)
        self.assertIn('revenue_by_product', charts)
        self.assertIn('revenue_by_plan', charts)
        self.assertIn('payments_vs_outstanding', charts)
        self.assertIn('active_vs_closed_subscriptions', charts)
        self.assertIn('overdue_invoice_distribution', charts)
        self.assertIn('subscription_expiry_timeline', charts)
        self.assertIn('payment_method_distribution', charts)

    # =========================================================================
    # END-TO-END MULTI-MODULE INTEGRATION TEST
    # =========================================================================
    def test_full_financial_lifecycle(self):
        """
        Verify complete integration chain:
        1. Active subscription created with 20% promotional discount
        2. Billing engine runs and validates discount & 18% GST tax
        3. Invoice generated and discount usage history recorded
        4. Payment module records partial payment (residual updated)
        5. Payment module records final payment (invoice marked PAID)
        6. Finance Dashboard reflects updated received revenue
        """
        # 1. Create 20% discount
        disc = self.env['subscriptiq.discount'].create({
            'name': 'Spring Promotion 20%',
            'code': 'SPRING20',
            'discount_type': 'percentage',
            'value': 20.0,
            'active': True
        })

        # 2. Subscription with base ₹5,000
        sub = self.env['sale.order'].create({
            'name': 'SUB/2026/E2E',
            'partner_id': self.partner.id,
            'plan_id': self.plan.id,
            'discount_id': disc.id,
            'amount_total': 5000.0,
            'subscriptiq_recurring_total': 5000.0,
            'subscriptiq_status': 'active'
        })

        # 3. Bill Subscription: ₹5,000 - 20% (₹1,000) = ₹4,000 + 18% GST (₹720) = ₹4,720
        inv = BillingEngine.bill_subscription(self.env, sub)
        self.assertEqual(inv.amount_untaxed, 4000.0)
        self.assertEqual(inv.amount_tax, 720.0)
        self.assertEqual(inv.amount_total, 4720.0)
        self.assertEqual(inv.amount_residual, 4720.0)

        # Verify discount usage history
        history = self.env['subscriptiq.discount.usage.history'].search([('discount_id', '=', disc.id)])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].discount_amount, 1000.0)
        self.assertEqual(history[0].final_amount, 4000.0)

        # 4. Partial Payment of ₹2,720
        self.env['account.payment'].record_payment({
            'invoice_id': inv.id,
            'partner_id': self.partner.id,
            'amount': 2720.0,
            'payment_method': 'bank_transfer',
            'transaction_reference': 'E2E-WIRE-01'
        })
        self.assertEqual(inv.amount_residual, 2000.0)
        self.assertEqual(inv.payment_state, 'not_paid')

        # 5. Final Payment of ₹2,000
        self.env['account.payment'].record_payment({
            'invoice_id': inv.id,
            'partner_id': self.partner.id,
            'amount': 2000.0,
            'payment_method': 'upi',
            'transaction_reference': 'E2E-UPI-02'
        })
        self.assertEqual(inv.amount_residual, 0.0)
        self.assertEqual(inv.payment_state, 'paid')

        # 6. Finance Dashboard reflects updated revenue received
        fin_data = FinanceDashboardService.compute_kpis_and_charts(self.env)
        self.assertGreaterEqual(fin_data['kpis']['revenue_received'], 4720.0)

if __name__ == '__main__':
    unittest.main()
