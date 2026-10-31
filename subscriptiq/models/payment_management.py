"""
SubscriptIQ Payment Management Module (Module 7)
Implements native payment recording, residual recalculation, partial & full settlement,
duplicate transaction prevention, payment reconciliation, and payment dashboard reporting.
"""

import datetime
from decimal import Decimal
from ..services.odoo_adapter import Model, models, fields, api, ValidationError, UserError

class AccountPayment(Model):
    _name = 'account.payment'
    _description = 'Payment Management & Allocation'

    name = fields.Char(string="Payment ID", required=True)
    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)
    invoice_id = fields.Many2one('account.move', string="Related Invoice", required=True)
    payment_method = fields.Selection([
        ('cash', 'Cash / Cheque'),
        ('upi', 'UPI / Instant Payment'),
        ('bank_transfer', 'Bank Transfer / Wire'),
        ('card', 'Credit / Debit Card'),
        ('other', 'Other Authorized Method')
    ], string="Payment Method", default='bank_transfer', required=True)
    amount = fields.Float(string="Payment Amount", required=True)
    payment_date = fields.Date(string="Payment Date", default=lambda self: datetime.date.today())
    transaction_reference = fields.Char(string="Transaction Reference")
    notes = fields.Text(string="Notes / Memo")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('reconciled', 'Reconciled'),
        ('cancelled', 'Cancelled')
    ], string="Payment Status", default='posted')
    
    @property
    def remaining_invoice_balance(self):
        if self.invoice_id:
            inv = self.invoice_id
            if hasattr(inv, 'amount_residual'):
                return float(inv.amount_residual)
            if hasattr(self, 'env') and isinstance(inv, int):
                inv_rec = self.env['account.move'].browse(inv)
                return float(getattr(inv_rec, 'amount_residual', 0.0))
        return 0.0

    def record_payment(self, *args, **kwargs):
        """
        Validates and records a customer payment against an invoice.
        Enforces strict accounting validations:
        - Amount > 0
        - Amount <= outstanding residual
        - Invoice belongs to selected customer
        - Prevent duplicate transaction references
        - Rejects cancelled invoices
        - Recalculates invoice residual balance
        - Marks invoice 'paid' only upon full settlement
        """
        env = getattr(self, 'env', None)
        values = {}
        if len(args) >= 2:
            potential_env, values = args[0], args[1]
            env = getattr(potential_env, 'env', potential_env)
        elif len(args) == 1:
            if isinstance(args[0], dict):
                values = args[0]
            else:
                env = getattr(args[0], 'env', args[0])
                values = kwargs.get('values', kwargs)
        else:
            values = kwargs.get('values', kwargs)

        if not env and hasattr(self, 'env'):
            env = self.env
        if hasattr(env, 'env'):
            env = env.env

        # 1. Target Invoice Validation
        inv_id = values.get('invoice_id')
        if not inv_id:
            raise ValidationError("An invoice must be selected to record payment.")

        invoice = env['account.move'].browse(inv_id)
        if not invoice:
            raise ValidationError("Target invoice not found in the database.")

        if invoice.state == 'cancel':
            raise UserError("Cannot record payment against a cancelled invoice.")

        if invoice.state != 'posted':
            raise UserError("Payments can only be recorded against confirmed / posted invoices.")

        if invoice.payment_state == 'paid':
            raise UserError(f"Invoice '{invoice.name}' is already fully settled and paid.")

        # 2. Customer Matching Validation
        customer_id = values.get('partner_id')
        inv_partner_id = invoice.partner_id.id if hasattr(invoice.partner_id, 'id') else invoice.partner_id
        if customer_id and int(customer_id) != int(inv_partner_id):
            raise ValidationError("Selected customer does not match the invoice billing party.")

        # 3. Payment Amount Validations
        pay_amount = float(values.get('amount', 0.0))
        if pay_amount <= 0.0:
            raise ValidationError("Payment amount must be greater than zero.")

        residual = float(getattr(invoice, 'amount_residual', invoice.amount_total))
        if pay_amount > residual + 0.01:
            raise ValidationError(
                f"Payment amount (₹{pay_amount:,.2f}) exceeds outstanding invoice balance (₹{residual:,.2f})."
            )

        # 4. Duplicate Transaction Reference Validation
        tx_ref = str(values.get('transaction_reference', '')).strip()
        if tx_ref and tx_ref != '':
            existing = env['account.payment'].search([
                ('transaction_reference', '=', tx_ref),
                ('state', 'in', ['posted', 'reconciled'])
            ])
            if existing:
                raise ValidationError(f"Duplicate transaction reference '{tx_ref}'. A posted payment already exists with this reference.")

        # 5. Method Validation
        method = values.get('payment_method', 'bank_transfer')
        valid_methods = ['cash', 'upi', 'bank_transfer', 'card', 'credit_card', 'other']
        if method not in valid_methods:
            raise ValidationError(f"Unsupported payment method '{method}'. Valid options: {valid_methods}.")

        # 6. Generate Payment Record
        pay_date = str(values.get('payment_date', datetime.date.today()))
        seq = env['ir.sequence'].next_by_code('account.payment') if 'ir.sequence' in env else None
        p_name = seq or f"PAY/{datetime.date.today().strftime('%Y%m%d')}/{env['account.payment'].search_count([]) + 1:04d}"

        company_id = invoice.company_id.id if hasattr(invoice.company_id, 'id') else (invoice.company_id or 1)

        payment = env['account.payment'].create({
            'name': p_name,
            'partner_id': inv_partner_id,
            'company_id': company_id,
            'invoice_id': invoice.id,
            'payment_method': method,
            'amount': pay_amount,
            'payment_date': pay_date,
            'transaction_reference': tx_ref,
            'notes': values.get('notes', ''),
            'state': 'posted'
        })

        # 7. Residual Recalculation & Settlement State Transition
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

        # 8. Cryptographic Audit Event
        if 'subscriptiq.audit.event' in env:
            env['subscriptiq.audit.event'].create({
                'event_type': 'payment_recorded',
                'user_id': env.user.id if hasattr(env, 'user') and env.user else 1,
                'company_id': company_id,
                'model_name': 'account.payment',
                'record_id': payment.id,
                'payload_json': f'{{"payment": "{payment.name}", "invoice": "{invoice.name}", "amount": {pay_amount}, "remaining_balance": {new_residual}, "method": "{method}"}}'
            })

        return payment

    @classmethod
    def get_payment_dashboard_metrics(cls, env, filters=None) -> dict:
        """
        Computes dedicated Payment Dashboard KPIs and breakdowns with multi-attribute filters.
        """
        filters = filters or {}
        today = datetime.date.today()
        first_of_month = today.replace(day=1)

        pay_domain = []
        if filters.get('partner_id'):
            pay_domain.append(('partner_id', '=', int(filters['partner_id'])))
        if filters.get('payment_method'):
            pay_domain.append(('payment_method', '=', filters['payment_method']))

        all_payments = env['account.payment'].search(pay_domain) if 'account.payment' in env else []

        total_received = 0.0
        payments_today = 0.0
        payments_this_month = 0.0
        reconciled_amount = 0.0
        reconciled_count = 0
        method_counts = {}

        for p in all_payments:
            if getattr(p, 'state', '') in ['posted', 'reconciled']:
                amt = float(getattr(p, 'amount', 0.0))
                total_received += amt
                m = getattr(p, 'payment_method', 'other')
                method_counts[m] = method_counts.get(m, 0.0) + amt

                pdate = getattr(p, 'payment_date', None)
                if pdate:
                    try:
                        pd = datetime.datetime.strptime(str(pdate)[:10], '%Y-%m-%d').date()
                        if pd == today:
                            payments_today += amt
                        if pd >= first_of_month:
                            payments_this_month += amt
                    except Exception:
                        pass

                if getattr(p, 'state', '') == 'reconciled':
                    reconciled_amount += amt
                    reconciled_count += 1

        # Invoices stats
        inv_domain = [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
        if filters.get('partner_id'):
            inv_domain.append(('partner_id', '=', int(filters['partner_id'])))

        all_invoices = env['account.move'].search(inv_domain) if 'account.move' in env else []
        outstanding_amount = 0.0
        overdue_amount = 0.0
        partial_payments_count = 0

        for inv in all_invoices:
            res = float(getattr(inv, 'amount_residual', 0.0))
            tot = float(getattr(inv, 'amount_total', 0.0))
            if res > 0.0:
                outstanding_amount += res
                if res < tot:
                    partial_payments_count += 1

                due = getattr(inv, 'invoice_date_due', None)
                if due:
                    try:
                        dd = datetime.datetime.strptime(str(due)[:10], '%Y-%m-%d').date()
                        if dd < today:
                            overdue_amount += res
                    except Exception:
                        pass

        return {
            'total_payments_received': round(total_received, 2),
            'payments_today': round(payments_today, 2),
            'payments_this_month': round(payments_this_month, 2),
            'outstanding_amount': round(outstanding_amount, 2),
            'overdue_amount': round(overdue_amount, 2),
            'partial_payments_count': partial_payments_count,
            'unallocated_payments_amount': 0.0,
            'reconciled_transactions_count': reconciled_count,
            'reconciled_transactions_amount': round(reconciled_amount, 2),
            'payment_method_breakdown': method_counts
        }
