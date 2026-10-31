"""
SubscriptIQ Subscription Adapter & Lifecycle Engine
Integrates natively with Odoo's sale.order, providing:
- Full subscription lifecycle: Draft -> Quotation -> Confirmed -> Active -> Closed / Paused
- Custom Daily Recurrence Extension
- Transactional Billing Guard integration to block duplicate billing
- Pre-invoice discount validation and tax accuracy
- Accounting invoice linkage (account.move)
"""

import datetime
from decimal import Decimal
from ..services.odoo_adapter import models, fields, api, UserError, ValidationError
from ..services.billing_protection import BillingProtectionEngine

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_subscription = fields.Boolean(string="Is Subscription", default=False)
    subscription_code = fields.Char(string="Subscription Identifier", copy=False)
    plan_id = fields.Many2one('subscriptiq.plan', string="Subscription Plan")
    stage = fields.Selection([
        ('draft', 'Draft'),
        ('quotation', 'Quotation Sent'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'Active / In Progress'),
        ('paused', 'Paused'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled')
    ], string="Subscription Status", default='draft')

    start_date = fields.Date(string="Start Date", default=lambda self: fields.Date.today())
    end_date = fields.Date(string="Expiry Date")
    last_invoice_date = fields.Date(string="Last Billing Date")
    next_invoice_date = fields.Date(string="Next Billing Date")

    discount_rule_id = fields.Many2one('subscriptiq.discount.rule', string="Applied Discount Rule")
    applied_discount_amount = fields.Float(string="Discount Amount Deducted", default=0.0)
    recurring_total = fields.Float(string="Recurring Total per Cycle", compute="_compute_recurring_total", store=True)

    # Daily Billing Recurrence Extension
    is_daily_billing = fields.Boolean(string="Custom Daily Recurrence Active", default=False)

    @api.depends('order_line', 'order_line.price_subtotal', 'discount_rule_id')
    def _compute_recurring_total(self):
        for order in self:
            lines = getattr(order, 'order_line', False)
            if lines and hasattr(lines, '__iter__'):
                subtotal = sum(getattr(line, 'price_subtotal', 0.0) for line in lines)
            else:
                subtotal = float(getattr(order, 'recurring_total', 0.0) or 0.0)
            order.recurring_total = max(0.0, subtotal - float(getattr(order, 'applied_discount_amount', 0.0) or 0.0))

    def action_quotation_send(self):
        """Transitions Draft -> Quotation."""
        for order in self:
            order.write({'subscriptiq_status': 'quotation', 'state': 'sent'})
        return True

    def action_confirm(self):
        """Transitions Quotation -> Confirmed."""
        for order in self:
            order.write({'subscriptiq_status': 'confirmed', 'state': 'sale'})
        return True

    def action_activate_subscription(self):
        """Transitions Confirmed -> Active."""
        for order in self:
            plan = order.subscriptiq_plan_id or order.plan_id
            if isinstance(plan, int):
                plan = self.env['subscriptiq.plan'].browse(plan)
            interval = getattr(plan, 'billing_interval', 'monthly') if plan else 'monthly'
            today = fields.Date.today()
            if interval == 'daily':
                next_ren = datetime.date.fromisoformat(str(today)[:10]) + datetime.timedelta(days=1)
            elif interval == 'weekly':
                next_ren = datetime.date.fromisoformat(str(today)[:10]) + datetime.timedelta(weeks=1)
            elif interval == 'yearly':
                next_ren = datetime.date.fromisoformat(str(today)[:10]) + datetime.timedelta(days=365)
            else:
                next_ren = datetime.date.fromisoformat(str(today)[:10]) + datetime.timedelta(days=30)

            order.write({
                'subscriptiq_status': 'active',
                'stage': 'in_progress',
                'subscription_code': getattr(order, 'subscription_code', False) or f"SUB/{order.id:05d}",
                'subscriptiq_next_renewal_date': str(next_ren),
                'next_renewal_date': str(next_ren),
                'next_invoice_date': str(next_ren)
            })
        return True

    def action_confirm_subscription(self):
        """Converts draft quotation into confirmed/active subscription."""
        self.action_confirm()
        return self.action_activate_subscription()

    def action_pause(self):
        """Pauses active subscription and suspends billing cycle."""
        for order in self:
            plan = order.subscriptiq_plan_id or order.plan_id
            if isinstance(plan, int):
                plan = self.env['subscriptiq.plan'].browse(plan)
            if plan and getattr(plan, 'pause_policy', '') == 'disallowed':
                raise UserError(f"Subscription plan '{plan.name}' strictly disallows pausing.")
            order.write({'subscriptiq_status': 'paused', 'stage': 'paused'})
        return True

    def action_resume(self):
        """Resumes a paused subscription."""
        for order in self:
            order.write({'subscriptiq_status': 'active', 'stage': 'in_progress'})
        return True

    def action_close(self, early=False, reason=""):
        """Closes subscription (Active -> Closed)."""
        for order in self:
            plan = order.subscriptiq_plan_id or order.plan_id
            if isinstance(plan, int):
                plan = self.env['subscriptiq.plan'].browse(plan)
            if early and plan and getattr(plan, 'early_closure_policy', '') == 'disallowed':
                raise UserError(f"Subscription plan '{plan.name}' disallows early termination without manager approval.")
            order.write({
                'subscriptiq_status': 'closed',
                'stage': 'closed',
                'end_date': fields.Date.today()
            })
        return True

    def action_early_close(self, reason="Customer requested early cancellation"):
        """Safely closes subscription prior to term expiry."""
        return self.action_close(early=True, reason=reason)

    def action_renew(self, extension_days=30):
        """Renews an active or expiring subscription."""
        for order in self:
            cur_end = order.end_date or fields.Date.today()
            cur_end_d = datetime.date.fromisoformat(str(cur_end)[:10])
            new_end = cur_end_d + datetime.timedelta(days=extension_days)
            order.write({'end_date': str(new_end), 'stage': 'in_progress'})
        return True

    def generate_recurring_invoice(self, billing_date=None):
        """
        Generates recurring invoice with transactional duplicate prevention.
        Acquires a billing reservation lock before invoice creation.
        """
        self.ensure_one()
        if self.stage != 'in_progress':
            raise UserError(f"Cannot generate invoice: Subscription '{self.name}' is in '{self.stage}' state.")

        billing_date = billing_date or self.next_invoice_date or fields.Date.today()
        bdate = datetime.date.fromisoformat(str(billing_date)[:10])

        plan = self.plan_id
        if isinstance(plan, int):
            plan = self.env['subscriptiq.plan'].browse(plan)
        interval = getattr(plan, 'billing_interval', 'monthly') if plan else 'monthly'

        # Compute period bounds
        period_start = bdate
        if interval == 'daily':
            period_end = period_start
            next_bdate = period_start + datetime.timedelta(days=1)
        elif interval == 'weekly':
            period_end = period_start + datetime.timedelta(days=6)
            next_bdate = period_start + datetime.timedelta(days=7)
        elif interval == 'monthly':
            # Approximate 30-day month
            period_end = period_start + datetime.timedelta(days=29)
            next_bdate = period_start + datetime.timedelta(days=30)
        elif interval == 'yearly':
            period_end = period_start + datetime.timedelta(days=364)
            next_bdate = period_start + datetime.timedelta(days=365)
        else:
            period_end = period_start + datetime.timedelta(days=29)
            next_bdate = period_start + datetime.timedelta(days=30)

        # 1. TRANSACTIONAL BILLING GUARD: Acquire reservation
        reservation = BillingProtectionEngine.acquire_billing_reservation(
            self.env, self, period_start, period_end
        )

        try:
            # 2. DISCOUNT AUDIT
            disc_info = BillingProtectionEngine.validate_and_apply_discounts(self, current_date=period_start)
            discount_to_apply = disc_info.get('calculated_discount', 0.0)

            # 3. CREATE INVOICE
            cid = self.company_id.id if hasattr(self.company_id, 'id') else (self.company_id or 1)
            partner_id = self.partner_id.id if hasattr(self.partner_id, 'id') else self.partner_id

            inv_vals = {
                'name': f"INV/{datetime.datetime.now().year}/{self.id:04d}-{str(period_start)[:7]}",
                'company_id': cid,
                'partner_id': partner_id,
                'subscription_id': self.id,
                'move_type': 'out_invoice',
                'state': 'posted',
                'payment_state': 'not_paid',
                'invoice_date': str(period_start),
                'invoice_date_due': str(period_start + datetime.timedelta(days=15)),
                'amount_total': float(self.recurring_total - discount_to_apply),
                'amount_residual': float(self.recurring_total - discount_to_apply),
                'discount_applied': discount_to_apply
            }

            invoice = self.env['account.move'].create(inv_vals)

            # 4. COMMIT RESERVATION
            BillingProtectionEngine.commit_billing_invoice(reservation, invoice)

            # Update subscription dates
            self.write({
                'last_invoice_date': str(period_start),
                'next_invoice_date': str(next_bdate)
            })

            # Update discount usage count if rule was applied
            rule_id = disc_info.get('rule_id')
            if rule_id:
                disc_rec = self.env['subscriptiq.discount.rule'].browse(rule_id)
                disc_rec.write({'usage_count': (disc_rec.usage_count or 0) + 1})

            return invoice

        except Exception as e:
            # Rollback reservation on failure
            BillingProtectionEngine.release_billing_reservation(reservation, reason=str(e))
            raise

class AccountMove(models.Model):
    _inherit = 'account.move'

    subscription_id = fields.Many2one('sale.order', string="Originating Subscription")
    discount_applied = fields.Float(string="Promotional Discount Applied", default=0.0)
    is_subscriptiq_flagged = fields.Boolean(string="Revenue Risk Case Active", default=False)
