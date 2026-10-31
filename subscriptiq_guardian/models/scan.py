# -*- coding: utf-8 -*-
from datetime import timedelta
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SubscriptiqGuardianScan(models.Model):
    _name = 'subscriptiq.guardian.scan'
    _description = 'Revenue Guardian Audit Scan'
    _order = 'create_date desc, id desc'

    name = fields.Char(
        string='Scan Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    scan_date = fields.Datetime(
        string='Scan Date',
        required=True,
        default=fields.Datetime.now,
        readonly=True
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('running', 'Running'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True
    )
    scan_type = fields.Selection(
        selection=[
            ('manual', 'Manual Trigger'),
            ('scheduled', 'Scheduled Cron'),
        ],
        string='Trigger Type',
        default='manual',
        required=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Triggered By',
        default=lambda self: self.env.user,
        readonly=True
    )
    risk_case_ids = fields.One2many(
        comodel_name='subscriptiq.guardian.risk.case',
        inverse_name='scan_id',
        string='Identified Risk Cases'
    )
    risk_case_count = fields.Integer(
        string='Risk Cases Found',
        compute='_compute_risk_metrics',
        store=True
    )
    total_exposure_amount = fields.Monetary(
        string='Total Financial Exposure',
        currency_field='currency_id',
        compute='_compute_risk_metrics',
        store=True
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company Currency',
        readonly=True
    )
    execution_notes = fields.Text(
        string='Execution Log & Notes',
        readonly=True
    )

    @api.depends('risk_case_ids', 'risk_case_ids.financial_impact')
    def _compute_risk_metrics(self):
        for scan in self:
            scan.risk_case_count = len(scan.risk_case_ids)
            scan.total_exposure_amount = sum(scan.risk_case_ids.mapped('financial_impact'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('subscriptiq.guardian.scan') or _('SCAN-%s') % fields.Date.today()
        return super().create(vals_list)

    def action_execute_scan(self):
        """Main entry point to perform revenue integrity audit."""
        for scan in self:
            if scan.state == 'running':
                raise UserError(_("Scan %s is currently in progress.") % scan.name)

            scan.write({'state': 'running', 'execution_notes': _("Starting revenue scan audit...\n")})
            logs = [f"Scan initiated at {fields.Datetime.now()} for company {scan.company_id.name}"]

            try:
                # 1. Scan Overdue Invoices
                overdue_count = scan._scan_overdue_invoices(logs)
                # 2. Scan Upcoming Due Invoices
                upcoming_count = scan._scan_upcoming_due_invoices(logs)
                # 3. Scan Suspicious Discounts
                discount_count = scan._scan_suspicious_discounts(logs)
                # 4. Scan Billing Discrepancies
                discrepancy_count = scan._scan_billing_discrepancies(logs)

                logs.append(
                    f"Scan successfully completed. Summary: Overdue: {overdue_count}, "
                    f"Upcoming: {upcoming_count}, Suspicious Discounts: {discount_count}, "
                    f"Discrepancies: {discrepancy_count}."
                )

                scan.write({
                    'state': 'completed',
                    'execution_notes': "\n".join(logs)
                })
            except Exception as e:
                _logger.exception("SubscriptIQ Revenue Guardian Scan Failed: %s", str(e))
                logs.append(f"CRITICAL ERROR ENCOUNTERED: {str(e)}")
                scan.write({
                    'state': 'failed',
                    'execution_notes': "\n".join(logs)
                })
        return True

    def _scan_overdue_invoices(self, logs):
        """Detect customer invoices with past payment due dates and open balance."""
        today = fields.Date.context_today(self)
        overdue_domain = [
            ('company_id', '=', self.company_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<', today)
        ]
        invoices = self.env['account.move'].search(overdue_domain)
        created_count = 0
        risk_case_obj = self.env['subscriptiq.guardian.risk.case']

        for inv in invoices:
            days_overdue = (today - inv.invoice_date_due).days
            # Determine severity based on aging
            if days_overdue >= 90:
                severity = 'critical'
            elif days_overdue >= 30:
                severity = 'high'
            elif days_overdue >= 15:
                severity = 'medium'
            else:
                severity = 'low'

            # Deduplication: Avoid duplicate active risk cases for identical issue and invoice
            existing = risk_case_obj.search([
                ('invoice_id', '=', inv.id),
                ('risk_type', '=', 'overdue_invoice'),
                ('status', 'in', ['new', 'investigating'])
            ], limit=1)

            if not existing:
                risk_case_obj.create({
                    'name': f"Overdue Invoice: {inv.name} ({days_overdue} days)",
                    'scan_id': self.id,
                    'partner_id': inv.partner_id.id,
                    'invoice_id': inv.id,
                    'company_id': self.company_id.id,
                    'risk_type': 'overdue_invoice',
                    'severity': severity,
                    'financial_impact': inv.amount_residual,
                    'reason': _(
                        "Invoice %(inv)s for customer %(partner)s has an overdue balance of %(amount).2f %(curr)s. "
                        "Maturity date was %(due)s (overdue by %(days)d days)."
                    ) % {
                        'inv': inv.name,
                        'partner': inv.partner_id.name,
                        'amount': inv.amount_residual,
                        'curr': inv.currency_id.name,
                        'due': inv.invoice_date_due,
                        'days': days_overdue,
                    },
                    'recommended_action': _(
                        "1. Send automated payment reminder to customer.\n"
                        "2. Verify if bank statement reconciliation is pending.\n"
                        "3. Escalate to collections team if aging exceeds 30 days."
                    )
                })
                created_count += 1

        logs.append(f"Overdue scanner reviewed {len(invoices)} candidate invoices, registered {created_count} new risk cases.")
        return created_count

    def _scan_upcoming_due_invoices(self, logs):
        """Identify invoices approaching due date within a 7-day window with high exposure."""
        today = fields.Date.context_today(self)
        horizon = today + timedelta(days=7)
        upcoming_domain = [
            ('company_id', '=', self.company_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '>=', today),
            ('invoice_date_due', '<=', horizon)
        ]
        invoices = self.env['account.move'].search(upcoming_domain)
        created_count = 0
        risk_case_obj = self.env['subscriptiq.guardian.risk.case']

        for inv in invoices:
            days_until_due = (inv.invoice_date_due - today).days
            # High balance nearing due date gets attention
            severity = 'medium' if inv.amount_residual > 5000 else 'low'

            existing = risk_case_obj.search([
                ('invoice_id', '=', inv.id),
                ('risk_type', '=', 'upcoming_due'),
                ('status', 'in', ['new', 'investigating'])
            ], limit=1)

            if not existing:
                risk_case_obj.create({
                    'name': f"Upcoming Due: {inv.name} due in {days_until_due}d",
                    'scan_id': self.id,
                    'partner_id': inv.partner_id.id,
                    'invoice_id': inv.id,
                    'company_id': self.company_id.id,
                    'risk_type': 'upcoming_due',
                    'severity': severity,
                    'financial_impact': inv.amount_residual,
                    'reason': _(
                        "Invoice %(inv)s is scheduled for payment on %(due)s (in %(days)d days). "
                        "Unpaid exposure is %(amount).2f %(curr)s."
                    ) % {
                        'inv': inv.name,
                        'due': inv.invoice_date_due,
                        'days': days_until_due,
                        'amount': inv.amount_residual,
                        'curr': inv.currency_id.name,
                    },
                    'recommended_action': _(
                        "Ensure early reminder notification is dispatched and payment mandate / card token is active."
                    )
                })
                created_count += 1

        logs.append(f"Upcoming due scanner checked {len(invoices)} invoices, registered {created_count} risk cases.")
        return created_count

    def _scan_suspicious_discounts(self, logs):
        """Detect excessive or suspicious invoice line discounts (> 25%)."""
        threshold = 25.0
        # Check standard account.move.line discount field on posted customer invoices
        lines = self.env['account.move.line'].search([
            ('company_id', '=', self.company_id.id),
            ('move_id.move_type', '=', 'out_invoice'),
            ('move_id.state', '=', 'posted'),
            ('display_type', '=', 'product'),
            ('discount', '>=', threshold)
        ])
        invoices = lines.mapped('move_id')
        created_count = 0
        risk_case_obj = self.env['subscriptiq.guardian.risk.case']

        for inv in invoices:
            flagged_lines = lines.filtered(lambda l: l.move_id == inv)
            max_discount = max(flagged_lines.mapped('discount'))
            
            # Calculate financial leak (approx discount amount)
            estimated_leak = sum((l.price_unit * l.quantity * (l.discount / 100.0)) for l in flagged_lines)
            severity = 'critical' if max_discount >= 50.0 else 'high'

            existing = risk_case_obj.search([
                ('invoice_id', '=', inv.id),
                ('risk_type', '=', 'suspicious_discount'),
                ('status', 'in', ['new', 'investigating'])
            ], limit=1)

            if not existing:
                risk_case_obj.create({
                    'name': f"High Discount Alert: {inv.name} (Max {max_discount:.1f}%)",
                    'scan_id': self.id,
                    'partner_id': inv.partner_id.id,
                    'invoice_id': inv.id,
                    'company_id': self.company_id.id,
                    'risk_type': 'suspicious_discount',
                    'severity': severity,
                    'financial_impact': estimated_leak,
                    'reason': _(
                        "Invoice %(inv)s contains lines with discount up to %(disc).1f%%, exceeding threshold (%(thresh).1f%%). "
                        "Estimated discounted sum: %(leak).2f %(curr)s."
                    ) % {
                        'inv': inv.name,
                        'disc': max_discount,
                        'thresh': threshold,
                        'leak': estimated_leak,
                        'curr': inv.currency_id.name,
                    },
                    'recommended_action': _(
                        "Validate commercial approval and contract terms for discount authorization. "
                        "Verify sales rep concession authorization policy."
                    )
                })
                created_count += 1

        logs.append(f"Suspicious discount scanner identified {len(invoices)} candidate invoices, registered {created_count} risk cases.")
        return created_count

    def _scan_billing_discrepancies(self, logs):
        """Detect invoice lines or invoice total discrepancies (e.g. untaxed + taxes != total, or negative totals)."""
        discrepancy_domain = [
            ('company_id', '=', self.company_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
        ]
        invoices = self.env['account.move'].search(discrepancy_domain)
        created_count = 0
        risk_case_obj = self.env['subscriptiq.guardian.risk.case']

        for inv in invoices:
            computed_total = inv.amount_untaxed + inv.amount_tax
            diff = abs(inv.amount_total - computed_total)

            # Rounding tolerance of 0.05
            if diff > 0.05 or inv.amount_total < 0:
                severity = 'critical' if diff > 50 else 'medium'
                existing = risk_case_obj.search([
                    ('invoice_id', '=', inv.id),
                    ('risk_type', '=', 'amount_discrepancy'),
                    ('status', 'in', ['new', 'investigating'])
                ], limit=1)

                if not existing:
                    risk_case_obj.create({
                        'name': f"Billing Discrepancy: {inv.name}",
                        'scan_id': self.id,
                        'partner_id': inv.partner_id.id,
                        'invoice_id': inv.id,
                        'company_id': self.company_id.id,
                        'risk_type': 'amount_discrepancy',
                        'severity': severity,
                        'financial_impact': diff or abs(inv.amount_total),
                        'reason': _(
                            "Discrepancy detected between computed header total (%(computed).2f) and actual recorded "
                            "total (%(actual).2f) on %(inv)s. Variance: %(diff).2f %(curr)s."
                        ) % {
                            'computed': computed_total,
                            'actual': inv.amount_total,
                            'inv': inv.name,
                            'diff': diff,
                            'curr': inv.currency_id.name,
                        },
                        'recommended_action': _(
                            "Review tax rounding configurations, manual journal adjustments, or ledger imbalance."
                        )
                    })
                    created_count += 1

        logs.append(f"Discrepancy scanner validated {len(invoices)} invoices, registered {created_count} risk cases.")
        return created_count

    @api.model
    def cron_execute_scheduled_scan(self):
        """Cron execution handler for automated scheduled revenue scans."""
        companies = self.env['res.company'].search([])
        for company in companies:
            scan = self.create({
                'company_id': company.id,
                'scan_type': 'scheduled',
            })
            scan.action_execute_scan()
        return True
