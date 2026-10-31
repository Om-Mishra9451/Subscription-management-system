"""
SubscriptIQ Statement Line and Matching Candidate Models
Represents individual imported bank transactions and candidate invoice match scores.
"""

from ..services.odoo_adapter import models, fields, api

class SubscriptiqPaymentImportLine(models.Model):
    _name = 'subscriptiq.payment.import.line'
    _description = 'Bank Statement Transaction Line'
    _order = 'transaction_date desc, id desc'

    batch_id = fields.Many2one('subscriptiq.payment.import', string="Import Batch", required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company or 1)
    transaction_date = fields.Date(string="Transaction Date", required=True)
    amount = fields.Float(string="Amount Received", required=True, default=0.0)
    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.ref('base.INR', raise_if_not_found=False) or 1)

    reference = fields.Char(string="Payment Reference / UTR")
    description = fields.Text(string="Statement Narration")
    partner_name = fields.Char(string="Reported Payer Name")
    partner_id = fields.Many2one('res.partner', string="Identified Customer")

    external_transaction_id = fields.Char(string="Bank Transaction ID", required=True, index=True)
    row_hash = fields.Char(string="Row Integrity Hash")

    state = fields.Selection([
        ('unmatched', 'Unmatched / Pending Review'),
        ('matched', 'Candidate Identified'),
        ('reconciled', 'Reconciled & Allocated'),
        ('rejected', 'Ignored / Rejected')
    ], string="Line Status", default='unmatched')

    candidate_ids = fields.One2many('subscriptiq.match.candidate', 'import_line_id', string="Matching Candidates")

class SubscriptiqMatchCandidate(models.Model):
    _name = 'subscriptiq.match.candidate'
    _description = 'Payment Match Candidate'
    _order = 'confidence desc'

    import_line_id = fields.Many2one('subscriptiq.payment.import.line', string="Bank Statement Line", required=True)
    invoice_id = fields.Many2one('account.move', string="Candidate Invoice", required=True)
    payment_id = fields.Many2one('account.payment', string="Created Reconciliation Payment")

    confidence = fields.Float(string="Confidence Score (0.00 - 1.00)", default=0.0)
    confidence_level = fields.Selection([
        ('high', 'High Confidence (>= 0.90)'),
        ('medium', 'Manual Review (0.70 - 0.89)'),
        ('low', 'Low Confidence (< 0.70)')
    ], string="Confidence Tier", default='medium')

    explanation = fields.Text(string="Scoring Rationale & Evidence")
    state = fields.Selection([
        ('proposed', 'Proposed Suggestion'),
        ('reconciled', 'Approved & Reconciled'),
        ('rejected', 'Rejected by Reviewer')
    ], string="Status", default='proposed')

    reviewed_by = fields.Many2one('res.users', string="Reviewer")
    reconciled_at = fields.Datetime(string="Reconciliation Timestamp")

    def action_approve_reconciliation(self):
        """Applies native Odoo reconciliation against target invoice."""
        from ..services.payment_matcher import PaymentMatcherEngine
        for cand in self:
            PaymentMatcherEngine.execute_reconciliation(self.env, cand, user_id=self.env.uid)
        return True
