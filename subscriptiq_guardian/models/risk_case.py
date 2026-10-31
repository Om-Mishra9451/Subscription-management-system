# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SubscriptiqGuardianRiskCase(models.Model):
    _name = 'subscriptiq.guardian.risk.case'
    _description = 'Revenue Guardian Risk Case'
    _order = 'create_date desc, severity desc, id desc'

    name = fields.Char(
        string='Case Title',
        required=True,
        index=True
    )
    scan_id = fields.Many2one(
        comodel_name='subscriptiq.guardian.scan',
        string='Originating Scan',
        ondelete='set null',
        index=True
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        required=True,
        index=True
    )
    invoice_id = fields.Many2one(
        comodel_name='account.move',
        string='Invoice Reference',
        domain="[('move_type', '=', 'out_invoice')]",
        ondelete='cascade',
        index=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Currency',
        readonly=True
    )
    risk_type = fields.Selection(
        selection=[
            ('overdue_invoice', 'Overdue Invoice'),
            ('upcoming_due', 'Upcoming Due Horizon'),
            ('suspicious_discount', 'Excessive / Suspicious Discount'),
            ('amount_discrepancy', 'Billing Amount Discrepancy'),
            ('duplicate_attempt', 'Duplicate Billing Attempt'),
        ],
        string='Risk Category',
        required=True,
        default='overdue_invoice',
        index=True
    )
    severity = fields.Selection(
        selection=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        string='Severity Level',
        required=True,
        default='medium',
        index=True
    )
    status = fields.Selection(
        selection=[
            ('new', 'New'),
            ('investigating', 'Investigating'),
            ('resolved', 'Resolved'),
            ('dismissed', 'Dismissed'),
        ],
        string='Status',
        required=True,
        default='new',
        index=True
    )
    financial_impact = fields.Monetary(
        string='Financial Impact / Exposure',
        currency_field='currency_id',
        default=0.0
    )
    reason = fields.Text(
        string='Detection Reason & Context',
        required=True
    )
    recommended_action = fields.Text(
        string='Recommended Action',
        help="Actionable recommendations generated to resolve or mitigate this revenue risk."
    )
    resolution_notes = fields.Text(
        string='Resolution Notes',
        help="Internal notes logged when resolving or dismissing the case."
    )
    assigned_user_id = fields.Many2one(
        comodel_name='res.users',
        string='Assigned Investigator',
        default=lambda self: self.env.user
    )

    def action_investigate(self):
        """Move case from New to Investigating."""
        for case in self:
            case.status = 'investigating'
        return True

    def action_resolve(self):
        """Mark risk case as Resolved."""
        for case in self:
            case.status = 'resolved'
        return True

    def action_dismiss(self):
        """Dismiss the risk case as false-positive or authorized exception."""
        for case in self:
            case.status = 'dismissed'
        return True

    def action_reopen(self):
        """Reopen case back to Investigating status."""
        for case in self:
            case.status = 'investigating'
        return True
