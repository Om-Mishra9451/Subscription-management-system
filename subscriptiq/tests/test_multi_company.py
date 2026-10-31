"""
SubscriptIQ Multi-Company Isolation Test Suite
Verifies that multi-tenant data, risk cases, billing guards, and revenue calculations
remain strictly isolated across distinct companies.
"""

import unittest
from subscriptiq.services.odoo_adapter import Environment
from subscriptiq.services.revenue_calculator import RevenueCalculator
from subscriptiq.services.billing_protection import BillingProtectionEngine

class TestMultiCompany(unittest.TestCase):

    def setUp(self):
        self.env = Environment()

    def test_multi_company_revenue_isolation(self):
        """Revenue calculations for Company 1 must ignore invoices and subscriptions of Company 2."""
        co1_id = 1
        co2_id = 2

        # Create active subscription in Company 1 (₹5,000/mo)
        p1 = self.env['subscriptiq.plan'].create({'name': 'Co1 Plan', 'code': 'P1', 'billing_interval': 'monthly', 'price': 5000.0})
        self.env['sale.order'].create({
            'name': 'SO-CO1',
            'is_subscription': True,
            'stage': 'in_progress',
            'plan_id': p1.id,
            'recurring_total': 5000.0,
            'company_id': co1_id
        })

        # Create active subscription in Company 2 (₹15,000/mo)
        p2 = self.env['subscriptiq.plan'].create({'name': 'Co2 Plan', 'code': 'P2', 'billing_interval': 'monthly', 'price': 15000.0})
        self.env['sale.order'].create({
            'name': 'SO-CO2',
            'is_subscription': True,
            'stage': 'in_progress',
            'plan_id': p2.id,
            'recurring_total': 15000.0,
            'company_id': co2_id
        })

        # Compute for Company 1
        metrics_co1 = RevenueCalculator.compute_dashboard_metrics(self.env, company_id=co1_id)
        self.assertEqual(metrics_co1['mrr'], 5000.00)
        self.assertEqual(metrics_co1['active_subscriptions'], 1)

        # Compute for Company 2
        metrics_co2 = RevenueCalculator.compute_dashboard_metrics(self.env, company_id=co2_id)
        self.assertEqual(metrics_co2['mrr'], 15000.00)
        self.assertEqual(metrics_co2['active_subscriptions'], 1)

    def test_billing_guards_scoped_by_company(self):
        """Identical subscription IDs in different companies do not collide in billing guards."""
        key1 = BillingProtectionEngine.generate_guard_key(company_id=1, subscription_id=10, period_start='2026-10-01', period_end='2026-10-31')
        key2 = BillingProtectionEngine.generate_guard_key(company_id=2, subscription_id=10, period_start='2026-10-01', period_end='2026-10-31')
        self.assertNotEqual(key1, key2)

if __name__ == '__main__':
    unittest.main()
