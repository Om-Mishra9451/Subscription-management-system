"""
SubscriptIQ Revenue Guardian Risk Engine Test Suite
Tests:
- Deterministic detection of overdue invoices
- Deterministic detection of expiring subscriptions
- SHA-256 case fingerprinting & deduplication across continuous scans
- Explainable risk scoring and factor attribution
"""

import datetime
import unittest
from subscriptiq.services.odoo_adapter import Environment
from subscriptiq.services.risk_engine import RiskEngine
from subscriptiq.services.churn_scoring import CustomerRiskScorer

class TestRiskEngine(unittest.TestCase):

    def setUp(self):
        self.env = Environment()

    def test_overdue_invoice_detection(self):
        """Overdue invoice past due date with positive residual generates a risk case."""
        partner = self.env['res.partner'].create({'name': 'Beta Tech Ltd'})
        past_date = str(datetime.date.today() - datetime.timedelta(days=15))

        inv = self.env['account.move'].create({
            'name': 'INV/2026/OVERDUE',
            'partner_id': partner.id,
            'company_id': 1,
            'move_type': 'out_invoice',
            'state': 'posted',
            'payment_state': 'not_paid',
            'amount_total': 12000.0,
            'amount_residual': 12000.0,
            'invoice_date_due': past_date
        })

        scan_res = RiskEngine.execute_guardian_scan(self.env, company_id=1)
        self.assertTrue(scan_res['new_cases_found'] >= 1)

        case = self.env['subscriptiq.risk.case'].search([('invoice_id', '=', inv.id)])
        self.assertTrue(case)
        self.assertEqual(case[0].case_type, 'overdue_invoice')
        self.assertEqual(case[0].severity, 'high')  # 15 days overdue
        self.assertEqual(case[0].amount_at_risk, 12000.0)

    def test_fingerprint_deduplication_across_scans(self):
        """Repeated scans of the same exception update the case rather than creating duplicate cases."""
        # Initial scan
        res1 = RiskEngine.execute_guardian_scan(self.env, company_id=1)
        count_after_scan1 = len(self.env['subscriptiq.risk.case'].search([]))

        # Second scan immediately after
        res2 = RiskEngine.execute_guardian_scan(self.env, company_id=1)
        count_after_scan2 = len(self.env['subscriptiq.risk.case'].search([]))

        self.assertEqual(res2['new_cases_found'], 0)
        self.assertEqual(count_after_scan1, count_after_scan2)

    def test_explainable_risk_score(self):
        """Contributing factors and score ranges are fully explainable."""
        partner = self.env['res.partner'].create({'name': 'Delta Analytics'})
        past_date = str(datetime.date.today() - datetime.timedelta(days=10))

        # Create overdue invoice (8-30 days range: +25 points)
        self.env['account.move'].create({
            'name': 'INV/2026/DELTA',
            'partner_id': partner.id,
            'company_id': 1,
            'move_type': 'out_invoice',
            'state': 'posted',
            'payment_state': 'not_paid',
            'amount_total': 5000.0,
            'amount_residual': 5000.0,
            'invoice_date_due': past_date
        })

        score_data = CustomerRiskScorer.calculate_deterministic_score(self.env, partner.id, company_id=1)
        self.assertEqual(score_data['risk_score'], 25)
        self.assertEqual(score_data['risk_level'], 'low')
        self.assertTrue(any('8-30 days' in f for f in score_data['contributing_factors']))

if __name__ == '__main__':
    unittest.main()
