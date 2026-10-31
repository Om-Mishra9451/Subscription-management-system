"""
SubscriptIQ Payment Management (Module 4)
Supports recording payments across multiple payment methods (Bank Transfer, Credit Card, Cash, UPI),
partial and full payments, residual balance updates, and accounting settlement.
"""

import datetime
from ..services.odoo_adapter import Model, models, fields, api, ValidationError, UserError

class AccountPayment(Model):
    _name = 'account.payment'
    _description = 'Payment Management'

    name = fields.Char(string="Payment Reference", required=True)
    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)
    invoice_id = fields.Many2one('account.move', string="Related Invoice", required=True)
    payment_method = fields.Selection([
        ('bank_transfer', 'Bank Wire / Transfer'),
        ('credit_card', 'Credit / Debit Card'),
        ('upi', 'UPI / Instant Payment'),
        ('cash', 'Cash / Cheque')
    ], string="Payment Method", default='bank_transfer', required=True)
    amount = fields.Float(string="Payment Amount", required=True)
    payment_date = fields.Date(string="Payment Date", default=lambda self: datetime.date.today())
    transaction_reference = fields.Char(string="Bank / Gateway Transaction Ref")
    notes = fields.Text(string="Notes")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted / Reconciled'),
        ('cancelled', 'Cancelled')
    ], string="Status", default='posted')

    def record_payment(self, *args, **kwargs):
        """
        Records a payment against an invoice, recalculates residual amount,
        and transitions the invoice to 'paid' if fully settled.
        """
        env = getattr(self, 'env', None)
        values = {}
        if len(args) == 2:
            env = args[0]
            values = args[1]
        elif len(args) == 1:
            if isinstance(args[0], dict):
                values = args[0]
            else:
                env = args[0]
                values = kwargs.get('values', kwargs)
        else:
            values = kwargs.get('values', kwargs)

        if not env and hasattr(self, 'env'):
            env = self.env
        inv_id = values.get('invoice_id')
        if not inv_id:
            raise ValidationError("An invoice must be selected to record payment.")

        invoice = env['account.move'].browse(inv_id)
        if not invoice:
            raise ValidationError("Target invoice not found.")

        if invoice.state != 'posted':
            raise UserError("Payments can only be recorded against confirmed / posted invoices.")

        if invoice.payment_state == 'paid':
            raise UserError("This invoice is already fully paid.")

        pay_amount = float(values.get('amount', 0.0))
        if pay_amount <= 0:
            raise ValidationError("Payment amount must be greater than zero.")

        residual = float(getattr(invoice, 'amount_residual', invoice.amount_total))
        if pay_amount > residual + 0.01:
            raise ValidationError(f"Payment amount (${pay_amount:,.2f}) exceeds outstanding residual (${residual:,.2f}).")

        # Create payment record
        seq = env['ir.sequence'].next_by_code('account.payment') if 'ir.sequence' in env else None
        p_name = seq or f"PAY/{datetime.date.today().strftime('%Y%m%d')}/{env['account.payment'].search_count([]) + 1:04d}"

        partner_id = invoice.partner_id.id if hasattr(invoice.partner_id, 'id') else invoice.partner_id
        company_id = invoice.company_id.id if hasattr(invoice.company_id, 'id') else (invoice.company_id or 1)

        payment = env['account.payment'].create({
            'name': p_name,
            'partner_id': partner_id,
            'company_id': company_id,
            'invoice_id': invoice.id,
            'payment_method': values.get('payment_method', 'bank_transfer'),
            'amount': pay_amount,
            'payment_date': values.get('payment_date', str(datetime.date.today())),
            'transaction_reference': values.get('transaction_reference', ''),
            'notes': values.get('notes', ''),
            'state': 'posted'
        })

        # Recalculate invoice residual balance
        new_residual = max(0.0, round(residual - pay_amount, 2))
        update_vals = {
            'amount_residual': new_residual
        }
        if new_residual <= 0.001:
            update_vals['payment_state'] = 'paid'
            update_vals['subscriptiq_risk_state'] = 'recovered'
            update_vals['subscriptiq_recovered_date'] = datetime.datetime.now()
            update_vals['subscriptiq_recovered_amount'] = invoice.amount_total
        else:
            update_vals['payment_state'] = 'not_paid'

        invoice.write(update_vals)

        # Audit event
        if 'subscriptiq.audit.event' in env:
            env['subscriptiq.audit.event'].create({
                'event_type': 'payment_recorded',
                'user_id': env.user.id if hasattr(env, 'user') and env.user else 1,
                'company_id': company_id,
                'model_name': 'account.payment',
                'record_id': payment.id,
                'payload_json': f'{{"payment": "{payment.name}", "invoice": "{invoice.name}", "amount": {pay_amount}, "new_residual": {new_residual}}}'
            })

        return payment
