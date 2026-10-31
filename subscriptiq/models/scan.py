"""
SubscriptIQ Scan and Business Rule Models
Tracks automated inspection scan history and configurable revenue assurance rules.
"""

from ..services.odoo_adapter import models, fields, api

class SubscriptiqScan(models.Model):
    _name = 'subscriptiq.scan'
    _description = 'Revenue Guardian Inspection Scan'
    _order = 'create_date desc'

    name = fields.Char(string="Scan Reference", required=True, default="New Scan")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company or 1, required=True)
    start_time = fields.Datetime(string="Scan Started At")
    end_time = fields.Datetime(string="Scan Completed At")
    state = fields.Selection([
        ('draft', 'Draft / Queued'),
        ('in_progress', 'Scanning In Progress'),
        ('completed', 'Completed Successfully'),
        ('warning', 'Completed with Warnings'),
        ('failed', 'Scan Failed')
    ], string="Scan Status", default='draft')

    records_scanned = fields.Integer(string="Total Records Inspected", default=0)
    cases_found = fields.Integer(string="New Risk Cases Created", default=0)
    error_count = fields.Integer(string="Exception Count", default=0)
    ruleset_version = fields.Char(string="Ruleset Version", default="2026.1")

    def action_execute_scan(self):
        """Triggers scan execution immediately via the RiskEngine service."""
        from ..services.risk_engine import RiskEngine
        for scan in self:
            RiskEngine.execute_guardian_scan(self.env, company_id=scan.company_id.id, scan_record=scan)
        return True

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
