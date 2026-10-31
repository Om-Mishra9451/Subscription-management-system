"""
SubscriptIQ Billing Guard Model
Maintains transactional billing reservation locks per subscription billing period.
Enforces unique period billing within each company to prevent duplicate billing.
"""

from ..services.odoo_adapter import models, fields

class SubscriptiqBillingGuard(models.Model):
    _name = 'subscriptiq.billing.guard'
    _description = 'Subscription Billing Period Guard'
    _sql_constraints = [
        ('sub_period_unique', 'unique(company_id, subscription_id, period_start, period_end)',
         'A billing reservation already exists for this subscription and period! Duplicate billing prevented.')
    ]

    company_id = fields.Many2one('res.company', string="Company", required=True)
    subscription_id = fields.Many2one('sale.order', string="Subscription", required=True)
    period_start = fields.Date(string="Billing Period Start", required=True)
    period_end = fields.Date(string="Billing Period End", required=True)
    invoice_id = fields.Many2one('account.move', string="Associated Generated Invoice")

    state = fields.Selection([
        ('reserved', 'Reserved (Lock Acquired)'),
        ('invoiced', 'Invoiced (Committed)'),
        ('cancelled', 'Cancelled (Released)')
    ], string="Guard State", default='reserved', required=True)

    idempotency_key = fields.Char(string="Idempotency Key", index=True, copy=False)
    invoiced_at = fields.Datetime(string="Invoice Generation Timestamp")
    notes = fields.Char(string="Notes / Rollback Reason")
