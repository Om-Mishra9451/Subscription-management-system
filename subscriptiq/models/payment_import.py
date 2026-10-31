"""
SubscriptIQ Payment Reconciliation Models
Manages CSV statement batches, imported statement lines, and intelligent candidate matches.
"""

from ..services.odoo_adapter import models, fields, api

class SubscriptiqPaymentImport(models.Model):
    _name = 'subscriptiq.payment.import'
    _description = 'Bank Statement Import Batch'
    _order = 'import_date desc'

    name = fields.Char(string="Batch Reference", required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company or 1, required=True)
    journal_id = fields.Many2one('account.journal', string="Bank Journal")
    file_name = fields.Char(string="Imported File Name")
    import_date = fields.Datetime(string="Import Timestamp", default=lambda self: fields.Datetime.now())

    transaction_count = fields.Integer(string="Total Transactions", default=0)
    total_amount = fields.Float(string="Total Batch Amount", default=0.0)

    state = fields.Selection([
        ('draft', 'Draft / Uploaded'),
        ('processing', 'Matching in Progress'),
        ('completed', 'Matching Complete'),
        ('reconciled', 'Fully Reconciled')
    ], string="Batch State", default='draft')

    line_ids = fields.One2many('subscriptiq.payment.import.line', 'batch_id', string="Transaction Lines")
