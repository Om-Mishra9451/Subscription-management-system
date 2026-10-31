"""
SubscriptIQ Rule Definition Model
Defines configurable, deterministic business rules for revenue assurance scans.
"""

from ..services.odoo_adapter import models, fields

class SubscriptiqRule(models.Model):
    _name = 'subscriptiq.rule'
    _description = 'Revenue Assurance Business Rule'

    name = fields.Char(string="Rule Name", required=True)
    code = fields.Char(string="Rule Code", required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company or 1)
    rule_type = fields.Selection([
        ('overdue', 'Overdue Invoices'),
        ('expiration', 'Expiring Subscriptions'),
        ('discount', 'Expired / Exhausted Discounts'),
        ('unmatched', 'Unmatched Bank Transactions'),
        ('duplicate', 'Duplicate Billing Prevention'),
        ('failed_payment', 'Failed Payment Attempts')
    ], string="Category", required=True, default='overdue')

    enabled = fields.Boolean(string="Active", default=True)
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string="Default Severity", default='medium', required=True)

    threshold = fields.Float(string="Threshold Parameter", default=1.0)
    version = fields.Char(string="Rule Version", default="1.0")
    condition_config = fields.Text(string="Condition JSON Config")
    effective_from = fields.Date(string="Effective From")
    effective_until = fields.Date(string="Effective Until")
