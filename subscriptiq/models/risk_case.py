"""
SubscriptIQ Risk Case Model
Represents an individual financial risk event or revenue leakage exception detected by Revenue Guardian.
Contains explainable evidence, severity, deterministic fingerprint, and verified recovery tracking.
"""

from ..services.odoo_adapter import models, fields, api

class SubscriptiqRiskCase(models.Model):
    _name = 'subscriptiq.risk.case'
    _description = 'Revenue Risk Case'
    _order = 'risk_score desc, detected_at desc'

    name = fields.Char(string="Case Reference", required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company or 1, required=True)
    rule_id = fields.Many2one('subscriptiq.rule', string="Triggering Rule")
    case_type = fields.Selection([
        ('overdue_invoice', 'Overdue Invoice'),
        ('expiring_subscription', 'Upcoming Subscription Expiry'),
        ('expired_discount', 'Expired / Exhausted Discount'),
        ('unmatched_payment', 'Unmatched Bank Transaction'),
        ('duplicate_billing', 'Duplicate Billing Attempt'),
        ('failed_payment', 'Failed Payment Transaction'),
        ('amount_discrepancy', 'Invoice Amount Discrepancy')
    ], string="Risk Category", required=True)

    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string="Severity", default='medium', required=True)

    state = fields.Selection([
        ('open', 'Open / Detected'),
        ('investigating', 'Under Investigation'),
        ('action_proposed', 'Recovery Proposed'),
        ('resolved', 'Resolved & Recovered'),
        ('ignored', 'Dismissed / Accepted Risk')
    ], string="Case Status", default='open', required=True)

    partner_id = fields.Many2one('res.partner', string="Customer")
    subscription_id = fields.Many2one('sale.order', string="Related Subscription")
    invoice_id = fields.Many2one('account.move', string="Related Invoice")
    payment_id = fields.Many2one('account.payment', string="Related Payment")

    amount_at_risk = fields.Float(string="Amount at Risk", default=0.0)
    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.ref('base.INR', raise_if_not_found=False) or 1)
    risk_score = fields.Integer(string="Risk Score (0-100)", default=50)

    explanation = fields.Text(string="Financial Risk Explanation")
    evidence = fields.Text(string="Supporting Audit Evidence")
    recommended_action = fields.Char(string="Recommended Remediation Action")

    fingerprint = fields.Char(string="Deterministic Case Fingerprint", index=True, copy=False)
    detected_at = fields.Datetime(string="Detection Timestamp")
    last_checked_at = fields.Datetime(string="Last Verified Timestamp")
    resolved_at = fields.Datetime(string="Resolution Timestamp")

    # Recovery Tracking
    recovered_amount = fields.Float(string="Verified Recovered Amount", default=0.0)
    recovery_verified = fields.Boolean(string="Recovery Verified via Accounting", default=False)
    resolution_notes = fields.Text(string="Resolution Notes")

    def action_investigate(self):
        """Moves case to investigating."""
        self.write({'state': 'investigating'})
        return True

    def action_dismiss(self):
        """Dismisses the case as accepted risk."""
        self.write({'state': 'ignored'})
        return True
