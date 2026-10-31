# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SubscriptiqGuardianRule(models.Model):
    _name = 'subscriptiq.guardian.rule'
    _description = 'Revenue Guardian Audit Rule'
    _order = 'sequence, id'

    name = fields.Char(
        string='Rule Name',
        required=True,
        translate=True
    )
    code = fields.Char(
        string='Rule Code',
        required=True,
        index=True,
        help="Unique technical identifier for the audit rule."
    )
    rule_type = fields.Selection(
        selection=[
            ('overdue_invoice', 'Overdue Invoice Scanner'),
            ('upcoming_due', 'Upcoming Due Date Watchdog'),
            ('suspicious_discount', 'Excessive / Suspicious Discount Detector'),
            ('amount_discrepancy', 'Billing Amount / Line Discrepancy Detector'),
        ],
        string='Rule Type',
        required=True,
        default='overdue_invoice'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    severity = fields.Selection(
        selection=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        string='Default Severity',
        required=True,
        default='medium'
    )
    threshold_days = fields.Integer(
        string='Threshold Days',
        default=7,
        help="Days overdue for overdue scans, or horizon window in days for upcoming due date alerts."
    )
    discount_threshold_pct = fields.Float(
        string='Discount Alert Threshold (%)',
        default=25.0,
        help="Invoices with line discount exceeding this percentage trigger a risk case."
    )
    description = fields.Text(
        string='Description',
        help="Internal explanation of what this audit rule validates."
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The audit rule code must be unique across the system.')
    ]
