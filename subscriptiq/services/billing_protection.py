"""
SubscriptIQ Transactional Billing Protection Engine
Implements zero-leakage billing guards, transactional reservation locks,
and strict pre-invoice discount validation to prevent duplicate billing and invalid discounting.
"""

import hashlib
import datetime
import logging
from decimal import Decimal
from .odoo_adapter import UserError, ValidationError

_logger = logging.getLogger(__name__)

class BillingProtectionEngine:
    """Transactional guard against duplicate billing and unearned discounts."""

    @classmethod
    def generate_guard_key(cls, company_id, subscription_id, period_start, period_end):
        """
        Creates an immutable idempotency key for a specific billing interval.
        """
        key_raw = f"{company_id}:{subscription_id}:{str(period_start)[:10]}:{str(period_end)[:10]}"
        return hashlib.sha256(key_raw.encode('utf-8')).hexdigest()

    @classmethod
    def acquire_billing_reservation(cls, env, subscription, period_start, period_end):
        """
        Atomically checks and creates a billing reservation before any invoice creation occurs.
        Raises UserError if a reservation or invoice already exists for this period.
        """
        cid = subscription.company_id.id if hasattr(subscription.company_id, 'id') else (subscription.company_id or 1)
        sub_id = subscription.id
        guard_key = cls.generate_guard_key(cid, sub_id, period_start, period_end)

        guard_model = env['subscriptiq.billing.guard']
        # Query existing reservations
        existing = guard_model.search([
            ('company_id', '=', cid),
            ('subscription_id', '=', sub_id),
            ('period_start', '=', str(period_start)[:10]),
            ('period_end', '=', str(period_end)[:10]),
            ('state', 'in', ['reserved', 'invoiced'])
        ])

        if existing:
            rec = existing[0]
            inv_ref = getattr(rec, 'invoice_id', False)
            inv_name = getattr(inv_ref, 'name', 'Existing Invoice') if inv_ref else 'Reserved Slot'
            _logger.warning("Duplicate billing attempt blocked for subscription %s period %s to %s (Guard ID: %s)",
                            sub_id, period_start, period_end, rec.id)
            raise UserError(
                f"[SubscriptIQ Billing Guard] Duplicate billing prevented! Subscription '{subscription.name}' "
                f"already has an active reservation/invoice ({inv_name}) for period {period_start} to {period_end}."
            )

        # Create transactional reservation lock
        reservation = guard_model.create({
            'company_id': cid,
            'subscription_id': sub_id,
            'period_start': str(period_start)[:10],
            'period_end': str(period_end)[:10],
            'state': 'reserved',
            'idempotency_key': guard_key,
        })

        return reservation

    @classmethod
    def commit_billing_invoice(cls, reservation, invoice):
        """
        Links the successfully generated invoice to the billing guard reservation and marks it 'invoiced'.
        """
        reservation.write({
            'invoice_id': invoice.id,
            'state': 'invoiced',
            'invoiced_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
        _logger.info("Billing reservation %s successfully committed to invoice %s", reservation.id, invoice.id)

    @classmethod
    def commit_billing_slot(cls, env, guard_key: str, invoice_id: int):
        """Finds reservation by guard key and commits to invoice."""
        guards = env['subscriptiq.billing.guard'].search([('idempotency_key', '=', guard_key)])
        if guards:
            inv = env['account.move'].browse(invoice_id) if isinstance(invoice_id, int) else invoice_id
            cls.commit_billing_invoice(guards[0], inv)

    @classmethod
    def release_billing_reservation(cls, reservation, reason="Invoice generation aborted"):
        """
        Rolls back the reservation if invoice generation encounters an error or is rolled back.
        """
        reservation.write({
            'state': 'cancelled',
            'notes': reason
        })
        _logger.warning("Billing reservation %s released: %s", reservation.id, reason)

    @classmethod
    def validate_and_apply_discounts(cls, subscription, current_date=None):
        """
        Pre-billing discount audit.
        Ensures discounts have not expired, are within quantity/spending thresholds,
        and have not exceeded their lifetime maximum usage limits.
        """
        current_date = current_date or datetime.date.today()
        cur_d_str = str(current_date)[:10]

        discount_rule = getattr(subscription, 'discount_rule_id', None)
        if not discount_rule:
            return {'valid': True, 'discount_rate': 0.0, 'reason': 'No discount rule attached'}
        if isinstance(discount_rule, int):
            discount_rule = subscription.env['subscriptiq.discount.rule'].browse(discount_rule)

        # Validate date validity
        start_date = getattr(discount_rule, 'start_date', None)
        end_date = getattr(discount_rule, 'end_date', None)

        if start_date and str(start_date)[:10] > cur_d_str:
            raise ValidationError(f"Discount '{discount_rule.name}' is not yet active (Starts {start_date}).")

        if end_date and str(end_date)[:10] < cur_d_str:
            raise ValidationError(f"Discount '{discount_rule.name}' has expired on {end_date}. Cannot apply to billing.")

        # Validate usage limit
        max_uses = getattr(discount_rule, 'max_usage_limit', 0)
        usage_count = getattr(discount_rule, 'usage_count', 0)
        if max_uses > 0 and usage_count >= max_uses:
            raise ValidationError(f"Discount '{discount_rule.name}' has reached its maximum usage limit ({usage_count}/{max_uses}).")

        # Validate minimum purchase amount
        min_amount = float(getattr(discount_rule, 'min_purchase_amount', 0.0))
        sub_total = float(getattr(subscription, 'recurring_total', getattr(subscription, 'amount_total', 0.0)))
        if min_amount > 0 and sub_total < min_amount:
            raise ValidationError(f"Subscription total (₹{sub_total:,.2f}) does not meet the minimum requirement of ₹{min_amount:,.2f} for discount '{discount_rule.name}'.")

        # Calculate discount
        disc_type = getattr(discount_rule, 'discount_type', 'percentage')
        disc_val = float(getattr(discount_rule, 'discount_value', 0.0))

        if disc_type == 'percentage':
            calculated_discount = (sub_total * (disc_val / 100.0))
        else:
            calculated_discount = min(disc_val, sub_total)

        return {
            'valid': True,
            'discount_type': disc_type,
            'discount_value': disc_val,
            'calculated_discount': calculated_discount,
            'rule_id': discount_rule.id
        }
