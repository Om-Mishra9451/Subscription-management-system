"""
SubscriptIQ Copilot Query Audit Log
Audit log storing sanitized user interactions, tool executions, and source-grounded answers.
"""

from ..services.odoo_adapter import models, fields

class SubscriptiqCopilotLog(models.Model):
    _name = 'subscriptiq.copilot.log'
    _description = 'AI Copilot Audit Query Log'
    _order = 'timestamp desc'

    user_id = fields.Many2one('res.users', string="User", required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company or 1)
    query = fields.Text(string="Sanitized User Query", required=True)
    response = fields.Text(string="AI Grounded Response")
    provider = fields.Char(string="AI Provider Used")
    model = fields.Char(string="Model Identifier")
    tool_calls = fields.Text(string="Tool Calls Executed (JSON)")
    timestamp = fields.Datetime(string="Timestamp", default=lambda self: fields.Datetime.now())
