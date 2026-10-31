"""
SubscriptIQ Match Candidate Model
Defines candidate match relationship between imported statement lines and customer invoices.
"""

from ..services.odoo_adapter import models, fields

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
