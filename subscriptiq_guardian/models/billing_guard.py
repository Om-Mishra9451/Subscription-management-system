# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SubscriptiqBillingGuard(models.Model):
    _name = 'subscriptiq.billing.guard'
    _description = 'Duplicate Billing Guard & Reservation Registry'
    _order = 'create_date desc, id desc'

    subscription_ref = fields.Char(
        string='Subscription Reference / ID',
        required=True,
        index=True,
        help="External subscription ID, contract ID, or recurring order reference."
    )
    period_start = fields.Date(
        string='Period Start Date',
        required=True,
        index=True
    )
    period_end = fields.Date(
        string='Period End Date',
        required=True,
        index=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    state = fields.Selection(
        selection=[
            ('reserved', 'Period Reserved'),
            ('invoiced', 'Invoiced & Billed'),
            ('cancelled', 'Cancelled / Released'),
        ],
        string='Billing State',
        default='reserved',
        required=True,
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
        string='Linked Invoice',
        ondelete='set null',
        index=True
    )
    expected_amount = fields.Monetary(
        string='Expected Billable Amount',
        currency_field='currency_id',
        default=0.0
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Currency',
        readonly=True
    )
    lock_token = fields.Char(
        string='Idempotency Lock Token',
        copy=False,
        help="Unique idempotency token passed from client/job to avoid duplicate concurrent calls."
    )

    _sql_constraints = [
        (
            'unique_subscription_period_company',
            'unique(subscription_ref, period_start, period_end, company_id)',
            'DUPLICATE BILLING PREVENTED: A billing reservation already exists for this subscription reference and billing period in this company!'
        )
    ]

    @api.constrains('period_start', 'period_end')
    def _check_period_dates(self):
        for record in self:
            if record.period_start and record.period_end and record.period_start > record.period_end:
                raise ValidationError(_("Period Start Date (%s) cannot be after Period End Date (%s).") % (
                    record.period_start, record.period_end
                ))

    @api.model
    def reserve_billing_period(self, subscription_ref, period_start, period_end, partner_id, company_id=None, expected_amount=0.0, lock_token=None):
        """
        Thread-safe billing reservation handler.
        Uses PostgreSQL unique constraint and ORM verification to prevent duplicate billing.
        """
        if not company_id:
            company_id = self.env.company.id

        # Check existing active or invoiced reservation
        existing = self.search([
            ('subscription_ref', '=', str(subscription_ref).strip()),
            ('period_start', '=', period_start),
            ('period_end', '=', period_end),
            ('company_id', '=', company_id),
            ('state', 'in', ['reserved', 'invoiced']),
        ], limit=1)

        if existing:
            err_msg = _(
                "Duplicate billing attempt detected for Subscription '%(sub)s' (Period: %(start)s to %(end)s). "
                "Current state is '%(state)s' (Record ID: %(id)d)."
            ) % {
                'sub': subscription_ref,
                'start': period_start,
                'end': period_end,
                'state': existing.state,
                'id': existing.id
            }
            # Automatically spawn a high-severity risk case
            self.env['subscriptiq.guardian.risk.case'].create({
                'name': f"Duplicate Billing Attempt: Sub #{subscription_ref}",
                'partner_id': partner_id,
                'invoice_id': existing.invoice_id.id if existing.invoice_id else False,
                'company_id': company_id,
                'risk_type': 'duplicate_attempt',
                'severity': 'critical',
                'financial_impact': expected_amount or existing.expected_amount,
                'reason': err_msg,
                'recommended_action': _(
                    "Abort duplicate invoice generation immediately. Investigate subscription scheduling or concurrent webhook payloads."
                )
            })
            raise UserError(err_msg)

        # Create new reservation
        reservation = self.create({
            'subscription_ref': str(subscription_ref).strip(),
            'period_start': period_start,
            'period_end': period_end,
            'partner_id': partner_id,
            'company_id': company_id,
            'expected_amount': expected_amount,
            'lock_token': lock_token,
            'state': 'reserved',
        })
        return reservation

    def action_link_invoice(self, invoice):
        """Link generated invoice to billing reservation and mark as invoiced."""
        self.ensure_one()
        if self.state == 'invoiced' and self.invoice_id and self.invoice_id != invoice:
            raise UserError(_("Billing period is already locked to invoice %s.") % self.invoice_id.name)
        
        self.write({
            'invoice_id': invoice.id,
            'state': 'invoiced',
        })
        return True

    def action_release_reservation(self):
        """Cancel reservation allowing period to be re-billed if prior run aborted cleanly."""
        for rec in self:
            if rec.state == 'invoiced' and rec.invoice_id and rec.invoice_id.state == 'posted':
                raise UserError(_("Cannot cancel reservation linked to a posted invoice (%s).") % rec.invoice_id.name)
            rec.state = 'cancelled'
        return True
