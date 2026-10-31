"""
SubscriptIQ Payment Reconciliation Test Suite
Tests:
- Bank statement CSV parsing and validation (headers, date formatting, positive amounts, duplicates)
- Deterministic multi-signal matching weights (0.50 ref, 0.30 amount, 0.15 partner, 0.05 date)
- Never reconciles solely on amount match
- Native accounting payment registration and verified recovered revenue updates
"""

import unittest
from subscriptiq.services.odoo_adapter import Environment, ValidationError, UserError
from subscriptiq.services.payment_matcher import PaymentMatcherEngine

SAMPLE_CSV_VALID = """date,amount,currency,reference,description,transaction_id,customer_name
2026-10-15,5000.00,INR,INV/2026/001,NEFT Brightloop Payment,TXN1001,Acme Corp
2026-10-16,1500.50,INR,INV/2026/002,IMPS Software Renewal,TXN1002,Wayne Enterprises
"""

SAMPLE_CSV_INVALID = """date,amount,currency,reference,transaction_id
invalid-date,not-a-number,INR,INV/2026/003,TXN1003
2026-10-18,-500.00,INR,INV/2026/004,TXN1004
"""

class TestPaymentMatcher(unittest.TestCase):

    def setUp(self):
        self.env = Environment()

    def test_csv_parsing_and_validation(self):
        """Valid rows accepted; invalid rows (date, negative amount) cleanly rejected."""
        res_valid = PaymentMatcherEngine.parse_and_validate_csv(SAMPLE_CSV_VALID)
        self.assertEqual(len(res_valid['accepted']), 2)
        self.assertEqual(len(res_valid['rejected']), 0)
        self.assertEqual(res_valid['total_amount'], 6500.50)

        res_invalid = PaymentMatcherEngine.parse_and_validate_csv(SAMPLE_CSV_INVALID)
        self.assertEqual(len(res_invalid['accepted']), 0)
        self.assertEqual(len(res_invalid['rejected']), 2)

    def test_matching_weights_and_confidence(self):
        """Exact reference (0.50) + exact amount (0.30) + partner (0.15) + date (0.05) = 1.00 high confidence."""
        partner = self.env['res.partner'].create({'name': 'Acme Corp'})
        invoice = self.env['account.move'].create({
            'name': 'INV/2026/001',
            'partner_id': partner.id,
            'company_id': 1,
            'move_type': 'out_invoice',
            'state': 'posted',
            'payment_state': 'not_paid',
            'amount_total': 5000.0,
            'amount_residual': 5000.0,
            'invoice_date': '2026-10-15'
        })

        import_line = self.env['subscriptiq.payment.import.line'].create({
            'batch_id': 1,
            'company_id': 1,
            'transaction_date': '2026-10-15',
            'amount': 5000.0,
            'reference': 'INV/2026/001',
            'description': 'NEFT INV/2026/001 Acme Corp',
            'partner_name': 'Acme Corp',
            'external_transaction_id': 'TXN1001'
        })

        candidates = PaymentMatcherEngine.match_transaction(self.env, import_line, company_id=1)
        self.assertTrue(len(candidates) >= 1)
        top_cand = candidates[0]
        self.assertEqual(top_cand['confidence'], 1.0)
        self.assertEqual(top_cand['confidence_level'], 'high')

    def test_never_reconcile_solely_on_amount(self):
        """Amount-only match must not reach high confidence (max 0.30/0.35, low confidence)."""
        partner = self.env['res.partner'].create({'name': 'Stark Industries'})
        invoice = self.env['account.move'].create({
            'name': 'INV/2026/999',
            'partner_id': partner.id,
            'company_id': 1,
            'move_type': 'out_invoice',
            'state': 'posted',
            'payment_state': 'not_paid',
            'amount_total': 5000.0,
            'amount_residual': 5000.0,
            'invoice_date': '2026-01-01'  # 9 months prior (no date score)
        })

        import_line = self.env['subscriptiq.payment.import.line'].create({
            'batch_id': 1,
            'company_id': 1,
            'transaction_date': '2026-10-15',
            'amount': 5000.0,
            'reference': 'UNKNOWN-REF-777',
            'description': 'Random Bank Transfer',
            'partner_name': 'Unknown Sender',
            'external_transaction_id': 'TXN9999'
        })

        candidates = PaymentMatcherEngine.match_transaction(self.env, import_line, company_id=1)
        # Because only amount matches (0.30), confidence is 0.30 (<0.60 threshold) and is rejected from candidate suggestions
        self.assertEqual(len(candidates), 0)

    def test_native_reconciliation_execution(self):
        """Native reconciliation registers account.payment and marks risk case resolved with verified recovered amount."""
        partner = self.env['res.partner'].create({'name': 'Wayne Enterprises'})
        invoice = self.env['account.move'].create({
            'name': 'INV/2026/002',
            'partner_id': partner.id,
            'company_id': 1,
            'move_type': 'out_invoice',
            'state': 'posted',
            'payment_state': 'not_paid',
            'amount_total': 3000.0,
            'amount_residual': 3000.0,
            'invoice_date': '2026-10-16'
        })

        risk_case = self.env['subscriptiq.risk.case'].create({
            'name': 'Overdue Case INV/2026/002',
            'company_id': 1,
            'case_type': 'overdue_invoice',
            'severity': 'high',
            'amount_at_risk': 3000.0,
            'invoice_id': invoice.id,
            'state': 'open'
        })

        import_line = self.env['subscriptiq.payment.import.line'].create({
            'batch_id': 1,
            'company_id': 1,
            'transaction_date': '2026-10-16',
            'amount': 3000.0,
            'reference': 'INV/2026/002',
            'description': 'INV/2026/002 Wayne Enterprises',
            'partner_name': 'Wayne Enterprises',
            'external_transaction_id': 'TXN1002'
        })

        candidate = self.env['subscriptiq.match.candidate'].create({
            'import_line_id': import_line.id,
            'invoice_id': invoice.id,
            'confidence': 1.0,
            'confidence_level': 'high',
            'state': 'proposed'
        })

        # Execute reconciliation
        res = PaymentMatcherEngine.execute_reconciliation(self.env, candidate, user_id=1)
        self.assertTrue(res['success'])
        self.assertEqual(res['new_payment_state'], 'paid')
        self.assertEqual(invoice.amount_residual, 0.0)

        # Verify risk case resolved and verified
        self.assertEqual(risk_case.state, 'resolved')
        self.assertTrue(risk_case.recovery_verified)
        self.assertEqual(risk_case.recovered_amount, 3000.0)

if __name__ == '__main__':
    unittest.main()
