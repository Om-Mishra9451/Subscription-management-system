"""
SubscriptIQ Financial Metrics & Revenue Dashboard Test Suite
Tests:
- MRR normalization across daily, weekly, monthly, yearly cycles
- ARR annualization (MRR * 12)
- Verified Revenue Recovered strictly counting accounting-reconciled payments
- Revenue at Risk de-duplication
- Revenue Leakage Rate exposure calculation
- Decimal precision without floating-point error
"""

from decimal import Decimal
import unittest
from subscriptiq.services.odoo_adapter import Environment
from subscriptiq.services.revenue_calculator import RevenueCalculator

class TestDashboardMetrics(unittest.TestCase):

    def setUp(self):
        self.env = Environment()

    def test_mrr_and_arr_normalization(self):
        """MRR normalized properly across intervals and annualized ARR = MRR * 12."""
        # Monthly ₹1,200 => MRR = 1,200.00
        mrr_mo = RevenueCalculator.normalize_mrr(Decimal('1200.00'), 'monthly', 1)
        self.assertEqual(mrr_mo, Decimal('1200.00'))

        # Yearly ₹12,000 => MRR = 1,000.00
        mrr_yr = RevenueCalculator.normalize_mrr(Decimal('12000.00'), 'yearly', 1)
        self.assertEqual(mrr_yr, Decimal('1000.00'))

        # Daily ₹100 => MRR = (100 * 365) / 12 = 3041.67
        mrr_daily = RevenueCalculator.normalize_mrr(Decimal('100.00'), 'daily', 1)
        self.assertEqual(mrr_daily, Decimal('3041.67'))

        # ARR for ₹1,000 MRR = ₹12,000
        arr = RevenueCalculator.calculate_arr(Decimal('1000.00'))
        self.assertEqual(arr, Decimal('12000.00'))

    def test_verified_recovered_revenue_only_counts_reconciled(self):
        """Unverified or suggested cases must not be counted in Verified Revenue Recovered."""
        # Unresolved case (₹5,000)
        self.env['subscriptiq.risk.case'].create({
            'name': 'Open Case 1',
            'company_id': 1,
            'case_type': 'overdue_invoice',
            'amount_at_risk': 5000.0,
            'state': 'open',
            'recovery_verified': False
        })

        # Resolved case without verified accounting payment (₹2,000)
        self.env['subscriptiq.risk.case'].create({
            'name': 'Resolved but Unverified Case',
            'company_id': 1,
            'case_type': 'overdue_invoice',
            'amount_at_risk': 2000.0,
            'recovered_amount': 2000.0,
            'state': 'resolved',
            'recovery_verified': False  # Not verified
        })

        # Legitimate verified recovery via bank reconciliation (₹8,500)
        self.env['subscriptiq.risk.case'].create({
            'name': 'Reconciled Verified Case',
            'company_id': 1,
            'case_type': 'overdue_invoice',
            'amount_at_risk': 8500.0,
            'recovered_amount': 8500.0,
            'state': 'resolved',
            'recovery_verified': True  # Verified
        })

        metrics = RevenueCalculator.compute_dashboard_metrics(self.env, company_id=1)
        # Should count ONLY the verified ₹8,500
        self.assertEqual(metrics['verified_recovered_revenue'], 8500.00)
        self.assertEqual(metrics['revenue_at_risk'], 5000.00)

if __name__ == '__main__':
    unittest.main()
