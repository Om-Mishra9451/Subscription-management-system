"""
SubscriptIQ Deterministic Rules Engine
Applies strict, auditable, explainable business rules across Odoo subscription, sales,
invoice, and payment records to identify financial leakage and risk exceptions.
Generates unique fingerprints to guarantee deterministic deduplication.
"""

import hashlib
import datetime
import logging
from decimal import Decimal

_logger = logging.getLogger(__name__)

class RulesEngine:
    """Deterministic detection engine for Revenue Guardian."""

    @staticmethod
    def generate_fingerprint(company_id, rule_code, target_model, target_id, qualifier=""):
        """
        Generates an immutable SHA-256 fingerprint for a risk incident.
        Prevents duplicate cases across continuous background scans.
        """
        raw = f"{company_id}:{rule_code}:{target_model}:{target_id}:{qualifier}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    @classmethod
    def evaluate_overdue_invoices(cls, env, company_id=None, days_threshold=1) -> list:
        """
        Rule: OVERDUE_INVOICE
        IF invoice_due_date < today AND invoice_residual > 0
        THEN create overdue risk case.
        """
        today = datetime.date.today()
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('amount_residual', '>', 0.0)
        ]
        if company_id:
            domain.append(('company_id', '=', company_id))

        invoices = env['account.move'].search(domain) if 'account.move' in env else []
        candidates = []

        for inv in invoices:
            due_date = getattr(inv, 'invoice_date_due', None)
            if not due_date:
                continue
            due_d = datetime.date.fromisoformat(str(due_date)[:10])
            overdue_days = (today - due_d).days
            if overdue_days >= days_threshold:
                residual = float(getattr(inv, 'amount_residual', 0.0))
                cid = inv.company_id.id if hasattr(inv.company_id, 'id') else (inv.company_id or company_id or 1)
                partner = inv.partner_id
                pid = partner.id if hasattr(partner, 'id') else partner

                # Determine severity based on days overdue
                if overdue_days > 30:
                    severity = 'critical'
                    risk_score = 85
                elif overdue_days > 7:
                    severity = 'high'
                    risk_score = 65
                else:
                    severity = 'medium'
                    risk_score = 45

                fingerprint = cls.generate_fingerprint(cid, 'OVERDUE_INVOICE', 'account.move', inv.id, str(due_d))

                candidates.append({
                    'name': f"Overdue Invoice {getattr(inv, 'name', '')} ({overdue_days}d)",
                    'company_id': cid,
                    'case_type': 'overdue_invoice',
                    'rule_code': 'OVERDUE_INVOICE',
                    'severity': severity,
                    'risk_score': risk_score,
                    'partner_id': pid,
                    'invoice_id': inv.id,
                    'subscription_id': getattr(inv, 'subscription_id', False) and (inv.subscription_id.id if hasattr(inv.subscription_id, 'id') else inv.subscription_id),
                    'amount_at_risk': residual,
                    'explanation': f"Customer invoice {getattr(inv, 'name', '')} is {overdue_days} days past due date ({due_d}). Outstanding residual is ₹{residual:,.2f}.",
                    'evidence': f"Due date: {due_d}, Amount residual: ₹{residual:,.2f}, Total: ₹{getattr(inv, 'amount_total', 0.0):,.2f}",
                    'recommended_action': 'send_reminder' if overdue_days <= 14 else 'escalate_recovery',
                    'fingerprint': fingerprint
                })

        return candidates

    @classmethod
    def evaluate_expiring_subscriptions(cls, env, company_id=None, warning_days=14) -> list:
        """
        Rule: EXPIRING_SUBSCRIPTION
        IF subscription_is_active AND next_renewal_date <= configured_warning_date
        THEN create renewal risk case.
        """
        today = datetime.date.today()
        warning_date = today + datetime.timedelta(days=warning_days)

        domain = [('stage', 'in', ['in_progress', 'active'])]
        if company_id:
            domain.append(('company_id', '=', company_id))

        subscriptions = env['sale.order'].search(domain) if 'sale.order' in env else []
        candidates = []

        for sub in subscriptions:
            end_date = getattr(sub, 'end_date', None) or getattr(sub, 'next_invoice_date', None)
            if not end_date:
                continue
            end_d = datetime.date.fromisoformat(str(end_date)[:10])
            days_left = (end_d - today).days

            if 0 <= days_left <= warning_days:
                cid = sub.company_id.id if hasattr(sub.company_id, 'id') else (sub.company_id or company_id or 1)
                partner = sub.partner_id
                pid = partner.id if hasattr(partner, 'id') else partner
                recurring_total = float(getattr(sub, 'recurring_total', getattr(sub, 'amount_total', 0.0)))

                severity = 'high' if days_left <= 3 else ('medium' if days_left <= 7 else 'low')
                risk_score = 75 if days_left <= 3 else (50 if days_left <= 7 else 30)

                fingerprint = cls.generate_fingerprint(cid, 'EXPIRING_SUBSCRIPTION', 'sale.order', sub.id, str(end_d))

                candidates.append({
                    'name': f"Expiring Subscription {getattr(sub, 'name', '')} in {days_left}d",
                    'company_id': cid,
                    'case_type': 'expiring_subscription',
                    'rule_code': 'EXPIRING_SUBSCRIPTION',
                    'severity': severity,
                    'risk_score': risk_score,
                    'partner_id': pid,
                    'subscription_id': sub.id,
                    'amount_at_risk': recurring_total,
                    'explanation': f"Subscription {getattr(sub, 'name', '')} expires in {days_left} days on {end_d}. Renewal proposal needed to prevent churn.",
                    'evidence': f"Expiry/Renewal Date: {end_d}, Value: ₹{recurring_total:,.2f}, Days remaining: {days_left}",
                    'recommended_action': 'generate_renewal_offer',
                    'fingerprint': fingerprint
                })

        return candidates

    @classmethod
    def evaluate_expired_discounts(cls, env, company_id=None) -> list:
        """
        Rule: EXPIRED_DISCOUNT
        IF discount_end_date < invoice_period_date OR usage_limit_reached
        THEN reject discount and log audit/risk case.
        """
        today = datetime.date.today()
        domain = [('stage', 'in', ['in_progress', 'active'])]
        if company_id:
            domain.append(('company_id', '=', company_id))

        subscriptions = env['sale.order'].search(domain) if 'sale.order' in env else []
        candidates = []

        for sub in subscriptions:
            # Check discount rule attachments
            discount_rule = getattr(sub, 'discount_rule_id', None)
            if not discount_rule:
                continue

            end_date = getattr(discount_rule, 'end_date', None)
            max_uses = getattr(discount_rule, 'max_usage_limit', 0)
            cur_uses = getattr(discount_rule, 'usage_count', 0)

            is_expired = False
            reason = ""

            if end_date and datetime.date.fromisoformat(str(end_date)[:10]) < today:
                is_expired = True
                reason = f"Discount '{discount_rule.name}' expired on {end_date}"
            elif max_uses > 0 and cur_uses >= max_uses:
                is_expired = True
                reason = f"Discount '{discount_rule.name}' reached maximum usage limit ({cur_uses}/{max_uses})"

            if is_expired:
                cid = sub.company_id.id if hasattr(sub.company_id, 'id') else (sub.company_id or company_id or 1)
                partner = sub.partner_id
                pid = partner.id if hasattr(partner, 'id') else partner
                discount_amt = float(getattr(sub, 'applied_discount_amount', 0.0))

                fingerprint = cls.generate_fingerprint(cid, 'EXPIRED_DISCOUNT', 'sale.order', sub.id, str(discount_rule.id))

                candidates.append({
                    'name': f"Invalid/Expired Discount on {getattr(sub, 'name', '')}",
                    'company_id': cid,
                    'case_type': 'expired_discount',
                    'rule_code': 'EXPIRED_DISCOUNT',
                    'severity': 'high',
                    'risk_score': 70,
                    'partner_id': pid,
                    'subscription_id': sub.id,
                    'amount_at_risk': discount_amt,
                    'explanation': f"{reason}. System prevented/flagged illicit discount application.",
                    'evidence': f"Rule ID: {discount_rule.id}, Name: {discount_rule.name}, Reason: {reason}",
                    'recommended_action': 'remove_invalid_discount',
                    'fingerprint': fingerprint
                })

        return candidates

    @classmethod
    def evaluate_unmatched_payments(cls, env, company_id=None, age_days_threshold=3) -> list:
        """
        Rule: UNMATCHED_PAYMENT
        Identifies imported bank transactions with no invoice match older than threshold.
        """
        domain = [('state', '=', 'unmatched')]
        if company_id:
            domain.append(('company_id', '=', company_id))

        unmatched_lines = env['subscriptiq.payment.import.line'].search(domain) if 'subscriptiq.payment.import.line' in env else []
        candidates = []
        today = datetime.date.today()

        for line in unmatched_lines:
            tx_date = getattr(line, 'transaction_date', None)
            tx_d = datetime.date.fromisoformat(str(tx_date)[:10]) if tx_date else today
            age_days = (today - tx_d).days

            if age_days >= age_days_threshold:
                cid = line.company_id.id if hasattr(line.company_id, 'id') else (company_id or 1)
                amt = float(getattr(line, 'amount', 0.0))
                partner = getattr(line, 'partner_id', None)
                pid = partner.id if hasattr(partner, 'id') else False

                fingerprint = cls.generate_fingerprint(cid, 'UNMATCHED_PAYMENT', 'subscriptiq.payment.import.line', line.id, str(line.external_transaction_id or ''))

                candidates.append({
                    'name': f"Unmatched Bank Transaction #{line.id} ({getattr(line, 'reference', '')})",
                    'company_id': cid,
                    'case_type': 'unmatched_payment',
                    'rule_code': 'UNMATCHED_PAYMENT',
                    'severity': 'medium' if age_days <= 7 else 'high',
                    'risk_score': 55 if age_days <= 7 else 70,
                    'partner_id': pid,
                    'amount_at_risk': amt,
                    'explanation': f"Bank transaction of ₹{amt:,.2f} received on {tx_d} ({age_days}d ago) has not been matched or allocated.",
                    'evidence': f"Ref: {getattr(line, 'reference', '')}, Desc: {getattr(line, 'description', '')}, ExtID: {getattr(line, 'external_transaction_id', '')}",
                    'recommended_action': 'manual_reconciliation_review',
                    'fingerprint': fingerprint
                })

        return candidates

    @classmethod
    def evaluate_failed_payments(cls, env, company_id=None) -> list:
        """
        Rule: FAILED_PAYMENT
        Identifies rejected or failed transactions in the payment journal.
        """
        domain = [('state', 'in', ['error', 'cancel', 'failed'])]
        if company_id:
            domain.append(('company_id', '=', company_id))

        failed_payments = env['account.payment'].search(domain) if 'account.payment' in env else []
        candidates = []

        for pmt in failed_payments:
            cid = pmt.company_id.id if hasattr(pmt.company_id, 'id') else (pmt.company_id or company_id or 1)
            partner = pmt.partner_id
            pid = partner.id if hasattr(partner, 'id') else partner
            amt = float(getattr(pmt, 'amount', 0.0))

            fingerprint = cls.generate_fingerprint(cid, 'FAILED_PAYMENT', 'account.payment', pmt.id)

            candidates.append({
                'name': f"Failed Payment Attempt {getattr(pmt, 'name', '')}",
                'company_id': cid,
                'case_type': 'failed_payment',
                'rule_code': 'FAILED_PAYMENT',
                'severity': 'high',
                'risk_score': 75,
                'partner_id': pid,
                'amount_at_risk': amt,
                'explanation': f"Payment attempt {getattr(pmt, 'name', '')} of ₹{amt:,.2f} failed or was cancelled.",
                'evidence': f"Payment Ref: {getattr(pmt, 'ref', '')}, State: {pmt.state}",
                'recommended_action': 'retry_payment_or_notify',
                'fingerprint': fingerprint
            })

        return candidates
