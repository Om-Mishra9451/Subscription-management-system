"""
SubscriptIQ Risk Snapshot Model
Stores periodic aggregate financial metrics and revenue leakage snapshots for fast dashboard loading.
"""

from ..services.odoo_adapter import models, fields

class SubscriptiqRiskSnapshot(models.Model):
    _name = 'subscriptiq.risk.snapshot'
    _description = 'Periodic Revenue Assurance Metric Snapshot'
    _order = 'snapshot_date desc'

    company_id = fields.Many2one('res.company', string="Company", required=True)
    snapshot_date = fields.Date(string="Snapshot Date", required=True)

    active_subscriptions = fields.Integer(string="Active Subscriptions Count", default=0)
    mrr = fields.Float(string="Monthly Recurring Revenue (MRR)", default=0.0)
    arr = fields.Float(string="Annualized Recurring Revenue (ARR)", default=0.0)

    revenue_at_risk = fields.Float(string="Revenue at Risk", default=0.0)
    recovered_revenue = fields.Float(string="Verified Recovered Revenue", default=0.0)
    overdue_amount = fields.Float(string="Overdue Invoices Amount", default=0.0)
    open_cases = fields.Integer(string="Open Risk Cases Count", default=0)
    leakage_rate = fields.Float(string="Revenue Leakage Rate (%)", default=0.0)

    overdue_debt = fields.Float(string="Overdue Debt", default=0.0)
    failed_payments = fields.Float(string="Failed Payments Risk", default=0.0)
    renewal_exposure = fields.Float(string="Renewal Exposure", default=0.0)
    unmatched_transactions = fields.Float(string="Unmatched Transactions Risk", default=0.0)
