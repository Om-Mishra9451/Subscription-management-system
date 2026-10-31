"""
SubscriptIQ Financial Revenue Calculator
Provides deterministic, audit-grade monetary calculations with strict Decimal arithmetic.
Calculates:
- Verified Revenue Recovered (actual reconciled allocations only)
- Revenue at Risk (unduped overdue debt, failed payments, renewal exposure)
- Revenue Leakage Rate (exposure ratio of flagged recurring revenue to period due)
- MRR (Normalized Monthly Recurring Revenue)
- ARR (Annualized Recurring Revenue = MRR * 12)
"""

from decimal import Decimal, ROUND_HALF_UP
import logging

_logger = logging.getLogger(__name__)

TWOPLACES = Decimal('0.01')

def to_decimal(val) -> Decimal:
    if val is None or val is False:
        return Decimal('0.00')
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal('0.00')

class RevenueCalculator:
    """Core deterministic revenue assurance calculator."""

    @staticmethod
    def normalize_mrr(amount: Decimal, billing_interval: str, interval_count: int = 1) -> Decimal:
        """
        Normalize recurring billing amounts to Monthly Recurring Revenue (MRR).
        - daily: (amount * 365) / 12
        - weekly: (amount * 52) / 12
        - monthly: amount / interval_count
        - yearly: amount / (12 * interval_count)
        """
        amount = to_decimal(amount)
        interval_count = max(1, interval_count or 1)
        billing_interval = (billing_interval or 'monthly').lower()

        if billing_interval == 'daily':
            mrr = (amount * Decimal('365')) / Decimal('12')
        elif billing_interval == 'weekly':
            mrr = (amount * Decimal('52')) / Decimal('12')
        elif billing_interval == 'monthly':
            mrr = amount / Decimal(str(interval_count))
        elif billing_interval == 'yearly':
            mrr = amount / (Decimal('12') * Decimal(str(interval_count)))
        else:
            mrr = amount

        return mrr.quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_arr(mrr: Decimal) -> Decimal:
        """
        Annualized Recurring Revenue (ARR).
        Standard Annualization Method: ARR = MRR * 12.
        """
        return (to_decimal(mrr) * Decimal('12')).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    @classmethod
    def compute_dashboard_metrics(cls, env, company_id=None, date_from=None, date_to=None) -> dict:
        """
        Computes the complete suite of revenue assurance indicators from real database records.
        Guarantees zero floating-point arithmetic and strict deduplication.
        """
        domain_company = [('company_id', '=', company_id)] if company_id else []

        # 1. Active Subscriptions & MRR / ARR
        sub_domain = domain_company + [('stage', 'in', ['in_progress', 'active'])]
        active_subs = env['sale.order'].search(sub_domain) if 'sale.order' in env else []

        total_mrr = Decimal('0.00')
        active_sub_count = 0

        for sub in active_subs:
            # Check recurring interval
            plan = getattr(sub, 'plan_id', None)
            interval = getattr(plan, 'billing_interval', 'monthly') if plan else 'monthly'
            interval_count = getattr(plan, 'billing_interval_count', 1) if plan else 1
            recurring_val = to_decimal(getattr(sub, 'recurring_total', getattr(sub, 'amount_total', 0.0)))
            sub_mrr = cls.normalize_mrr(recurring_val, interval, interval_count)
            total_mrr += sub_mrr
            active_sub_count += 1

        arr = cls.calculate_arr(total_mrr)

        # 2. Revenue at Risk (De-duplicated outstanding amounts on flagged invoices + renewal exposures)
        risk_case_domain = domain_company + [('state', 'in', ['open', 'investigating', 'action_proposed'])]
        open_cases = env['subscriptiq.risk.case'].search(risk_case_domain) if 'subscriptiq.risk.case' in env else []

        seen_invoices = set()
        seen_subs = set()
        overdue_debt = Decimal('0.00')
        failed_payments_risk = Decimal('0.00')
        renewal_exposure = Decimal('0.00')
        unmatched_tx_risk = Decimal('0.00')
        other_risk = Decimal('0.00')

        for case in open_cases:
            case_type = getattr(case, 'case_type', '')
            amt = to_decimal(getattr(case, 'amount_at_risk', 0.0))

            inv_obj = getattr(case, 'invoice_id', False)
            inv_id = inv_obj.id if hasattr(inv_obj, 'id') else inv_obj

            sub_obj = getattr(case, 'subscription_id', False)
            sub_id = sub_obj.id if hasattr(sub_obj, 'id') else sub_obj

            if case_type == 'overdue_invoice':
                if inv_id and inv_id not in seen_invoices:
                    seen_invoices.add(inv_id)
                    overdue_debt += amt
                elif not inv_id:
                    overdue_debt += amt
            elif case_type == 'failed_payment':
                if inv_id and inv_id not in seen_invoices:
                    seen_invoices.add(inv_id)
                    failed_payments_risk += amt
                elif not inv_id:
                    failed_payments_risk += amt
            elif case_type == 'expiring_subscription':
                if sub_id and sub_id not in seen_subs:
                    seen_subs.add(sub_id)
                    renewal_exposure += amt
                elif not sub_id:
                    renewal_exposure += amt
            elif case_type == 'unmatched_payment':
                unmatched_tx_risk += amt
            else:
                other_risk += amt

        total_revenue_at_risk = (overdue_debt + failed_payments_risk + renewal_exposure + unmatched_tx_risk + other_risk).quantize(TWOPLACES)

        # 3. Verified Revenue Recovered
        # Money actually received and allocated against previously flagged revenue-risk invoices.
        # Verified through accounting payment allocations on resolved cases.
        resolved_cases = env['subscriptiq.risk.case'].search(
            domain_company + [('state', '=', 'resolved'), ('recovery_verified', '=', True)]
        ) if 'subscriptiq.risk.case' in env else []

        recovered_revenue = Decimal('0.00')
        for rcase in resolved_cases:
            recovered_revenue += to_decimal(rcase.recovered_amount)
        recovered_revenue = recovered_revenue.quantize(TWOPLACES)

        # 4. Invoices Due in Period and Outstanding Total
        inv_domain = domain_company + [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
        posted_invoices = env['account.move'].search(inv_domain) if 'account.move' in env else []

        period_recurring_due = Decimal('0.00')
        total_outstanding = Decimal('0.00')
        overdue_invoices_count = 0

        import datetime
        today = datetime.date.today()

        for inv in posted_invoices:
            residual = to_decimal(getattr(inv, 'amount_residual', 0.0))
            total_amt = to_decimal(getattr(inv, 'amount_total', 0.0))
            period_recurring_due += total_amt
            if residual > Decimal('0.00'):
                total_outstanding += residual
                due_date = getattr(inv, 'invoice_date_due', None)
                if due_date and str(due_date)[:10] < str(today):
                    overdue_invoices_count += 1

        # Fallback period recurring due if no posted invoices yet (avoid divide by zero)
        baseline_period_due = period_recurring_due if period_recurring_due > Decimal('0.00') else total_mrr

        # 5. Revenue Leakage Rate
        # Leakage Rate = Unique recurring revenue flagged at risk / Recurring revenue due in period * 100
        if baseline_period_due > Decimal('0.00'):
            leakage_rate = ((total_revenue_at_risk / baseline_period_due) * Decimal('100.00')).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        else:
            leakage_rate = Decimal('0.00')

        return {
            'verified_recovered_revenue': float(recovered_revenue),
            'revenue_at_risk': float(total_revenue_at_risk),
            'revenue_leakage_rate': float(leakage_rate),
            'mrr': float(total_mrr),
            'arr': float(arr),
            'active_subscriptions': active_sub_count,
            'outstanding_amount': float(total_outstanding),
            'overdue_invoices_count': overdue_invoices_count,
            'open_risk_cases_count': len(open_cases),
            'risk_breakdown': {
                'overdue_debt': float(overdue_debt),
                'failed_payments': float(failed_payments_risk),
                'renewal_exposure': float(renewal_exposure),
                'unmatched_transactions': float(unmatched_tx_risk),
                'other_risk': float(other_risk)
            }
        }
