"""
SubscriptIQ Company Settings Extension
Stores company-specific revenue assurance configuration, risk thresholds, and automation policies.
"""

from ..services.odoo_adapter import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    subscriptiq_enabled = fields.Boolean(
        string="Enable SubscriptIQ Revenue Assurance",
        default=True,
        help="Activates continuous revenue monitoring and protection for this company."
    )
    overdue_warning_days = fields.Integer(
        string="Overdue Invoice Grace Days",
        default=1,
        help="Number of days past invoice due date before generating an overdue risk case."
    )
    expiry_warning_days = fields.Integer(
        string="Subscription Expiry Warning Days",
        default=14,
        help="Days prior to subscription end date to alert for renewal."
    )
    auto_scan_interval_minutes = fields.Integer(
        string="Automated Scan Interval (Minutes)",
        default=30,
        help="Frequency of background Revenue Guardian inspection scans."
    )
    require_reconciliation_approval = fields.Boolean(
        string="Require Reconciliation Approval",
        default=True,
        help="Enforces dual authorization before posting bank payment allocations."
    )
    leakage_alert_threshold = fields.Float(
        string="Leakage Rate Warning Threshold (%)",
        default=5.0,
        help="Sends notification if Revenue Leakage Rate exceeds this percentage."
    )
