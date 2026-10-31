"""
SubscriptIQ Subscription & Product Adapter Test Suite
Tests:
- Product variant extra price calculation (₹1000 base + ₹560 variant = ₹1560)
- Subscription lifecycle: Draft -> Confirmed -> Active -> Paused -> Resumed -> Closed
- Plan validation: date constraints, min quantity
- Custom Daily Recurrence Extension
"""

import datetime
import unittest
from subscriptiq.services.odoo_adapter import Environment, ValidationError, UserError
from subscriptiq.models.product_extension import ProductProduct
from subscriptiq.models.plan_extension import SubscriptiqPlan
from subscriptiq.models.subscription_adapter import SaleOrder

class TestSubscriptionAdapter(unittest.TestCase):

    def setUp(self):
        self.env = Environment()

    def test_product_variant_pricing(self):
        """Product variant extra surcharge added to template sales price."""
        product = self.env['product.product'].create({
            'name': 'Business Software (Odoo Branded)',
            'list_price': 1000.0,
            'variant_extra_price': 560.0
        })
        self.assertEqual(product.computed_effective_price, 1560.0)

    def test_plan_date_validation(self):
        """Plan with start date after end date must raise ValidationError."""
        plan = self.env['subscriptiq.plan'].create({
            'name': 'Annual Enterprise',
            'code': 'ENT-YR',
            'billing_interval': 'yearly',
            'availability_start_date': '2026-12-31',
            'availability_end_date': '2026-01-01'
        })
        with self.assertRaises(ValidationError):
            plan._check_availability_dates()

    def test_subscription_lifecycle(self):
        """Draft -> Confirmed / Active -> Paused -> Resumed -> Closed."""
        plan = self.env['subscriptiq.plan'].create({
            'name': 'Standard Monthly',
            'code': 'STD-MO',
            'billing_interval': 'monthly',
            'price': 2500.0,
            'pause_policy': 'allowed',
            'early_closure_policy': 'allowed_prorated'
        })

        sub = self.env['sale.order'].create({
            'name': 'SO-TEST-001',
            'is_subscription': True,
            'stage': 'draft',
            'plan_id': plan.id,
            'company_id': 1
        })

        # Confirm subscription
        sub.action_confirm_subscription()
        self.assertEqual(sub.stage, 'in_progress')
        self.assertTrue(sub.subscription_code)

        # Pause subscription
        sub.action_pause()
        self.assertEqual(sub.stage, 'paused')

        # Resume subscription
        sub.action_resume()
        self.assertEqual(sub.stage, 'in_progress')

        # Early close
        sub.action_early_close()
        self.assertEqual(sub.stage, 'closed')

    def test_daily_recurrence_extension(self):
        """Custom daily recurring billing increments by 1 day."""
        plan = self.env['subscriptiq.plan'].create({
            'name': 'Daily Cloud Compute',
            'code': 'DAILY-COMP',
            'billing_interval': 'daily',
            'price': 100.0
        })

        sub = self.env['sale.order'].create({
            'name': 'SO-DAILY-001',
            'is_subscription': True,
            'stage': 'in_progress',
            'plan_id': plan.id,
            'recurring_total': 100.0,
            'start_date': '2026-04-01',
            'next_invoice_date': '2026-04-01',
            'company_id': 1
        })

        invoice = sub.generate_recurring_invoice(billing_date='2026-04-01')
        self.assertEqual(invoice.amount_total, 100.0)
        self.assertEqual(str(sub.next_invoice_date)[:10], '2026-04-02')

if __name__ == '__main__':
    unittest.main()
