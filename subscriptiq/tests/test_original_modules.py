"""
SubscriptIQ Original Modules Automated Test Suite
Exhaustively tests the 5 core modules of the Subscription Management System:
- Module 1: User Management, Authentication & RBAC
- Module 2: Product & Plan Configuration, Variant Surcharges, Discounts & Taxes
- Module 3: Quotation Templates & Subscription Lifecycle State Machine
- Module 4: Automated Recurring Billing & Payment Settlement
- Module 5: Business Reporting & Finance Dashboard Aggregation
"""

import unittest
import datetime
from decimal import Decimal
from subscriptiq.services.odoo_adapter import Environment, ValidationError, UserError
from subscriptiq.models.user_management import ResUsers
from subscriptiq.services.billing_engine import BillingEngine
from subscriptiq.services.revenue_calculator import RevenueCalculator

class TestOriginalCoreModules(unittest.TestCase):

    def setUp(self):
        self.env = Environment()
        self.company = self.env['res.company'].create({'name': 'Brightloop Software Corp'})
        self.env.company = self.company

    # =========================================================================
    # MODULE 1: USER MANAGEMENT AND ACCESS CONTROL
    # =========================================================================

    def test_module1_password_complexity_validation(self):
        """Enforces >8 characters with uppercase, lowercase, and special character."""
        # Valid: 9+ chars, upper, lower, special
        self.assertTrue(ResUsers.validate_password_complexity("StrongP@ss1"))
        self.assertTrue(ResUsers.validate_password_complexity("BrightLoop#2026"))

        # Invalid: 8 or fewer chars
        self.assertFalse(ResUsers.validate_password_complexity("Str0ng!")) # 7 chars
        self.assertFalse(ResUsers.validate_password_complexity("Short1!A")) # 8 chars exactly

        # Invalid: Missing uppercase
        self.assertFalse(ResUsers.validate_password_complexity("weakpass1@word"))

        # Invalid: Missing lowercase
        self.assertFalse(ResUsers.validate_password_complexity("WEAKPASS1@WORD"))

        # Invalid: Missing special character
        self.assertFalse(ResUsers.validate_password_complexity("NoSpecialChar123"))

    def test_module1_user_registration_and_unique_email(self):
        """Creates user, verifies partner association, and enforces unique email."""
        user = ResUsers.create_user(self.env, {
            'name': 'Sarah Analyst',
            'login': 'sarah@brightloop.io',
            'password': 'SecureP@ssword2026',
            'role': 'staff'
        })
        self.assertEqual(user.login, 'sarah@brightloop.io')
        self.assertEqual(user.role, 'staff')
        self.assertTrue(user.partner_id)

        # Duplicate email must raise ValidationError
        with self.assertRaises(ValidationError):
            ResUsers.create_user(self.env, {
                'name': 'Duplicate Sarah',
                'login': 'sarah@brightloop.io',
                'password': 'AnotherP@ssword2026',
                'role': 'customer'
            })

    def test_module1_authentication_and_password_reset(self):
        """Tests credential authentication and secure email-based token reset."""
        ResUsers.create_user(self.env, {
            'name': 'David Customer',
            'login': 'david@acme.com',
            'password': 'InitialP@ssword1',
            'role': 'customer'
        })

        # Valid login
        auth_user = ResUsers.authenticate(self.env, 'david@acme.com', 'InitialP@ssword1')
        self.assertTrue(auth_user)
        self.assertEqual(auth_user.name, 'David Customer')

        # Invalid login
        bad_auth = ResUsers.authenticate(self.env, 'david@acme.com', 'WrongP@ssword99')
        self.assertFalse(bad_auth)

        # Password reset flow
        token = ResUsers.request_password_reset(self.env, 'david@acme.com')
        self.assertTrue(token)

        # Reset with new valid password
        success = ResUsers.reset_password_with_token(self.env, token, 'NewBrandNewP@ss2')
        self.assertTrue(success)

        # Verify old password fails and new password works
        self.assertFalse(ResUsers.authenticate(self.env, 'david@acme.com', 'InitialP@ssword1'))
        self.assertTrue(ResUsers.authenticate(self.env, 'david@acme.com', 'NewBrandNewP@ss2'))

    def test_module1_rbac_permissions(self):
        """Verifies Admin vs Staff vs Customer privilege boundaries."""
        admin = ResUsers.create_user(self.env, {'name': 'Admin User', 'login': 'admin@bl.io', 'password': 'AdminP@ssword1', 'role': 'admin'})
        staff = ResUsers.create_user(self.env, {'name': 'Staff User', 'login': 'staff@bl.io', 'password': 'StaffP@ssword1', 'role': 'staff'})
        customer = ResUsers.create_user(self.env, {'name': 'Client User', 'login': 'client@bl.io', 'password': 'ClientP@ssword1', 'role': 'customer'})

        # Admin can do all
        self.assertTrue(admin.check_permission('create_staff', 'res.users'))
        self.assertTrue(admin.check_permission('manage_settings', 'res.config.settings'))

        # Staff cannot create staff or manage admin settings
        self.assertFalse(staff.check_permission('create_staff', 'res.users'))
        self.assertFalse(staff.check_permission('manage_settings', 'res.config.settings'))
        self.assertTrue(staff.check_permission('manage_invoices', 'account.move'))

        # Customer can only read own and download invoices
        self.assertTrue(customer.check_permission('read_own', 'sale.order'))
        self.assertTrue(customer.check_permission('download_invoice', 'account.move'))
        self.assertFalse(customer.check_permission('manage_invoices', 'account.move'))

    # =========================================================================
    # MODULE 2: PRODUCT AND PLAN CONFIGURATION
    # =========================================================================

    def test_module2_product_variant_pricing_hackathon_example(self):
        """
        Original Hackathon Example:
        Base Product: Business Software, Base Price: ₹1,000
        Variant: Default (₹0 extra) => ₹1,000
        Variant: Odoo Brand (+₹560 extra) => ₹1,560.
        """
        tmpl = self.env['product.template'].create({
            'name': 'Business Software',
            'product_type': 'service',
            'list_price': 1000.0,
            'standard_price': 400.0
        })

        attr_brand = self.env['product.attribute'].create({'name': 'Brand'})
        val_default = self.env['product.attribute.value'].create({
            'name': 'Default',
            'attribute_id': attr_brand.id,
            'price_extra': 0.0
        })
        val_odoo = self.env['product.attribute.value'].create({
            'name': 'Odoo Brand',
            'attribute_id': attr_brand.id,
            'price_extra': 560.0
        })

        # Variant 1: Default
        p_default = self.env['product.product'].create({
            'product_tmpl_id': tmpl.id,
            'attribute_value_ids': [val_default],
            'price_extra': 0.0
        })
        self.assertEqual(p_default.sales_price, 1000.0)

        # Variant 2: Odoo Brand (+₹560)
        p_odoo = self.env['product.product'].create({
            'product_tmpl_id': tmpl.id,
            'attribute_value_ids': [val_odoo],
            'price_extra': 0.0
        })
        self.assertEqual(p_odoo.sales_price, 1560.0)

    def test_module2_plan_billing_frequencies(self):
        """Tests plan configuration across daily, weekly, monthly, and yearly cycles."""
        p_daily = self.env['subscriptiq.plan'].create({
            'name': 'Daily Cloud Plan',
            'billing_interval': 'daily',
            'price': 50.0
        })
        self.assertEqual(p_daily.billing_interval, 'daily')

        p_yearly = self.env['subscriptiq.plan'].create({
            'name': 'Annual Enterprise Plan',
            'billing_interval': 'yearly',
            'price': 12000.0
        })
        self.assertEqual(p_yearly.billing_interval, 'yearly')

    def test_module2_discount_rules_and_expiration(self):
        """Tests discount validation, percentage/fixed calculations, and expiration dates."""
        today = datetime.date.today()
        disc_active = self.env['subscriptiq.discount'].create({
            'name': 'Launch Promo 20%',
            'code': 'LAUNCH20',
            'discount_type': 'percentage',
            'value': 20.0,
            'min_purchase_amount': 500.0,
            'start_date': str(today - datetime.timedelta(days=5)),
            'end_date': str(today + datetime.timedelta(days=15)),
            'max_usage_limit': 10
        })

        # 20% on ₹1,000 = ₹200
        deduction = disc_active.validate_and_calculate(1000.0, quantity=1, eval_date=today)
        self.assertEqual(deduction, 200.0)

        # Test expired discount rejection
        disc_expired = self.env['subscriptiq.discount'].create({
            'name': 'Old Promo',
            'code': 'OLDPROMO',
            'discount_type': 'fixed',
            'value': 100.0,
            'start_date': str(today - datetime.timedelta(days=30)),
            'end_date': str(today - datetime.timedelta(days=1))
        })
        with self.assertRaises(ValidationError):
            disc_expired.validate_and_calculate(1000.0, eval_date=today)

    def test_module2_tax_calculations(self):
        """Tests GST 18% calculation with tax-exclusive and tax-inclusive pricing."""
        tax_excl = self.env['account.tax'].create({
            'name': 'GST 18% Exclusive',
            'amount_type': 'percent',
            'amount': 18.0,
            'price_include': False
        })
        res_excl = tax_excl.compute_all(1000.0, quantity=1)
        self.assertEqual(res_excl['total_excluded'], 1000.0)
        self.assertEqual(res_excl['tax_amount'], 180.0)
        self.assertEqual(res_excl['total_included'], 1180.0)

        tax_incl = self.env['account.tax'].create({
            'name': 'VAT 10% Inclusive',
            'amount_type': 'percent',
            'amount': 10.0,
            'price_include': True
        })
        res_incl = tax_incl.compute_all(1100.0, quantity=1)
        self.assertEqual(res_incl['total_included'], 1100.0)
        self.assertEqual(res_incl['total_excluded'], 1000.0)
        self.assertEqual(res_incl['tax_amount'], 100.0)

    # =========================================================================
    # MODULE 3: QUOTATION AND SUBSCRIPTION WORKFLOW
    # =========================================================================

    def test_module3_quotation_template_and_subscription_lifecycle(self):
        """
        Tests Quotation Templates and Mandatory Lifecycle:
        Draft -> Quotation -> Confirmed -> Active -> Paused -> Resumed -> Closed.
        """
        cust = self.env['res.partner'].create({'name': 'Brightstar Corp', 'email': 'sales@brightstar.io'})
        plan = self.env['subscriptiq.plan'].create({'name': 'Monthly SaaS', 'billing_interval': 'monthly', 'price': 1500.0})

        # 1. Create Quotation from Template
        quote = self.env['sale.order'].create({
            'partner_id': cust.id,
            'company_id': self.company.id,
            'subscriptiq_plan_id': plan.id,
            'subscriptiq_status': 'draft',
            'subscriptiq_recurring_total': 1500.0
        })
        self.assertEqual(quote.subscriptiq_status, 'draft')

        # 2. Transition Draft -> Quotation (Send Quote)
        quote.action_quotation_send()
        self.assertEqual(quote.subscriptiq_status, 'quotation')

        # 3. Transition Quotation -> Confirmed
        quote.action_confirm()
        self.assertEqual(quote.subscriptiq_status, 'confirmed')

        # 4. Activate Subscription (Confirmed -> Active)
        quote.action_activate_subscription()
        self.assertEqual(quote.subscriptiq_status, 'active')
        self.assertTrue(quote.subscriptiq_next_renewal_date)

        # 5. Pause Subscription
        quote.action_pause()
        self.assertEqual(quote.subscriptiq_status, 'paused')

        # 6. Resume Subscription
        quote.action_resume()
        self.assertEqual(quote.subscriptiq_status, 'active')

        # 7. Close Subscription (Active -> Closed)
        quote.action_close(early=True, reason="Customer Request")
        self.assertEqual(quote.subscriptiq_status, 'closed')

    # =========================================================================
    # MODULE 4: AUTOMATED BILLING AND PAYMENTS
    # =========================================================================

    def test_module4_automated_billing_and_payment_settlement(self):
        """
        Tests automated invoice generation for active due subscriptions,
        duplicate billing guard, partial payment, and final invoice settlement.
        """
        cust = self.env['res.partner'].create({'name': 'Zenith Media', 'email': 'ap@zenith.com'})
        plan = self.env['subscriptiq.plan'].create({'name': 'Weekly Retainer', 'billing_interval': 'weekly', 'price': 2000.0})

        today = datetime.date.today()

        sub = self.env['sale.order'].create({
            'name': 'SUB-ZENITH-01',
            'partner_id': cust.id,
            'company_id': self.company.id,
            'subscriptiq_plan_id': plan.id,
            'subscriptiq_status': 'active',
            'subscriptiq_recurring_total': 2000.0,
            'subscriptiq_next_renewal_date': str(today) # Due today
        })

        # 1. Automated Billing Execution
        invoice = BillingEngine.bill_subscription(self.env, sub, eval_date=today)
        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.payment_state, 'not_paid')
        # Subtotal ₹2,000 + GST 18% (₹360) = ₹2,360
        self.assertEqual(invoice.amount_total, 2360.0)
        self.assertEqual(invoice.amount_residual, 2360.0)

        # 2. Verify Duplicate Billing Protection
        with self.assertRaises(UserError):
            BillingEngine.bill_subscription(self.env, sub, eval_date=today)

        # 3. Partial Payment (Pay ₹1,000 of ₹2,360)
        p1 = self.env['account.payment'].record_payment(self.env, {
            'invoice_id': invoice.id,
            'amount': 1000.0,
            'payment_method': 'bank_transfer',
            'transaction_reference': 'TXN-WIRE-001'
        })
        self.assertEqual(invoice.amount_residual, 1360.0)
        self.assertEqual(invoice.payment_state, 'not_paid')

        # 4. Final Payment (Pay remaining ₹1,360)
        p2 = self.env['account.payment'].record_payment(self.env, {
            'invoice_id': invoice.id,
            'amount': 1360.0,
            'payment_method': 'credit_card',
            'transaction_reference': 'TXN-CARD-002'
        })
        self.assertEqual(invoice.amount_residual, 0.0)
        self.assertEqual(invoice.payment_state, 'paid')
        self.assertEqual(invoice.subscriptiq_risk_state, 'recovered')

    # =========================================================================
    # MODULE 5: REPORTING AND FINANCE DASHBOARD
    # =========================================================================

    def test_module5_business_finance_dashboard_metrics(self):
        """Tests the 10 business indicators and visual breakdown charts."""
        p_monthly = self.env['subscriptiq.plan'].create({'name': 'Standard Cloud', 'billing_interval': 'monthly', 'price': 1000.0})
        p_daily = self.env['subscriptiq.plan'].create({'name': 'Daily Micro', 'billing_interval': 'daily', 'price': 100.0})

        cust = self.env['res.partner'].create({'name': 'Prime Industries', 'is_company': True})

        # Active Monthly Sub: MRR = 1,000
        self.env['sale.order'].create({
            'name': 'SUB-01',
            'partner_id': cust.id,
            'company_id': self.company.id,
            'subscriptiq_plan_id': p_monthly.id,
            'subscriptiq_status': 'active',
            'subscriptiq_recurring_total': 1000.0
        })

        # Active Daily Sub: MRR = (100 * 365) / 12 = 3041.67
        self.env['sale.order'].create({
            'name': 'SUB-02',
            'partner_id': cust.id,
            'company_id': self.company.id,
            'subscriptiq_plan_id': p_daily.id,
            'subscriptiq_status': 'active',
            'subscriptiq_recurring_total': 100.0
        })

        # Invoice: Total ₹5,000, Residual ₹2,000 (Received = ₹3,000)
        self.env['account.move'].create({
            'name': 'INV-FIN-01',
            'partner_id': cust.id,
            'company_id': self.company.id,
            'move_type': 'out_invoice',
            'state': 'posted',
            'amount_total': 5000.0,
            'amount_residual': 2000.0
        })

        metrics = RevenueCalculator.compute_business_finance_dashboard(self.env)

        # Check 10 KPIs
        self.assertEqual(metrics['active_subscriptions'], 2)
        self.assertEqual(metrics['revenue_received'], 3000.0)
        self.assertEqual(metrics['outstanding_amount'], 2000.0)
        self.assertAlmostEqual(metrics['mrr'], 4041.67, places=2)
        self.assertAlmostEqual(metrics['arr'], 48500.04, places=2)
        self.assertTrue('payments_vs_outstanding' in metrics['charts'])
        self.assertTrue('overdue_aging' in metrics['charts'])
        self.assertTrue('revenue_by_plan' in metrics['charts'])

if __name__ == '__main__':
    unittest.main()
