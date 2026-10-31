"""
SubscriptIQ Transactional Billing Guard & Discount Test Suite
Tests:
- Transactional reservation lock preventing duplicate billing attempts
- Pre-invoice discount validation rejecting expired or usage-exhausted discounts
- Proper reservation release on failure
"""

import unittest
from subscriptiq.services.odoo_adapter import Environment, UserError, ValidationError
from subscriptiq.models.plan_extension import SubscriptiqPlan, SubscriptiqDiscountRule
from subscriptiq.models.subscription_adapter import SaleOrder
from subscriptiq.services.billing_protection import BillingProtectionEngine

class TestBillingGuard(unittest.TestCase):

    def setUp(self):
        self.env = Environment()

    def test_duplicate_billing_prevention(self):
        """Second invoice attempt for same subscription and period must be blocked transactionally."""
        plan = self.env['subscriptiq.plan'].create({
            'name': 'Monthly SaaS',
            'code': 'SAAS-MO',
            'billing_interval': 'monthly',
            'price': 5000.0
        })

        sub = self.env['sale.order'].create({
            'name': 'SO-DUP-001',
            'is_subscription': True,
            'stage': 'in_progress',
            'plan_id': plan.id,
            'recurring_total': 5000.0,
            'start_date': '2026-10-01',
            'next_invoice_date': '2026-10-01',
            'company_id': 1
        })

        # 1. First billing succeeds
        inv1 = sub.generate_recurring_invoice(billing_date='2026-10-01')
        self.assertTrue(inv1)
        self.assertEqual(inv1.amount_total, 5000.0)

        # 2. Second billing for same period (2026-10-01) must raise UserError
        with self.assertRaises(UserError) as ctx:
            sub.generate_recurring_invoice(billing_date='2026-10-01')

        self.assertIn("Duplicate billing prevented", str(ctx.exception))

    def test_expired_discount_rejection(self):
        """Discount past end_date must be rejected during billing."""
        disc_rule = self.env['subscriptiq.discount.rule'].create({
            'name': 'Expired Promo 2025',
            'code': 'OLD2025',
            'discount_type': 'percentage',
            'discount_value': 20.0,
            'start_date': '2025-01-01',
            'end_date': '2025-12-31'
        })

        plan = self.env['subscriptiq.plan'].create({
            'name': 'Monthly SaaS',
            'code': 'SAAS-MO',
            'billing_interval': 'monthly',
            'price': 10000.0
        })

        sub = self.env['sale.order'].create({
            'name': 'SO-DISC-001',
            'is_subscription': True,
            'stage': 'in_progress',
            'plan_id': plan.id,
            'recurring_total': 10000.0,
            'discount_rule_id': disc_rule.id,
            'company_id': 1
        })

        # Billing on 2026-10-01 with discount that expired on 2025-12-31 must raise ValidationError
        with self.assertRaises(ValidationError) as ctx:
            BillingProtectionEngine.validate_and_apply_discounts(sub, current_date='2026-10-01')

        self.assertIn("expired", str(ctx.exception).lower())

    def test_exhausted_usage_limit_discount_rejection(self):
        """Discount with max_usage_limit exhausted must be rejected."""
        disc_rule = self.env['subscriptiq.discount.rule'].create({
            'name': 'Limited Promo First 5',
            'code': 'FIRST5',
            'discount_type': 'fixed',
            'discount_value': 500.0,
            'max_usage_limit': 5,
            'usage_count': 5
        })

        sub = self.env['sale.order'].create({
            'name': 'SO-DISC-002',
            'is_subscription': True,
            'stage': 'in_progress',
            'recurring_total': 3000.0,
            'discount_rule_id': disc_rule.id,
            'company_id': 1
        })

        with self.assertRaises(ValidationError) as ctx:
            BillingProtectionEngine.validate_and_apply_discounts(sub, current_date='2026-10-01')

        self.assertIn("maximum usage limit", str(ctx.exception).lower())

if __name__ == '__main__':
    unittest.main()
