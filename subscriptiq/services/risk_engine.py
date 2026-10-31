"""
SubscriptIQ Continuous Revenue Guardian Risk Engine
Orchestrates scanning runs across Odoo records, manages risk case lifecycle,
computes deterministic risk priorities, batch processing, and prevents duplicate alerts.
"""

import datetime
import logging
from .rules_engine import RulesEngine
from .odoo_adapter import UserError

_logger = logging.getLogger(__name__)

class RiskEngine:
    """Orchestration engine for Revenue Guardian automated scans."""

    @classmethod
    def execute_guardian_scan(cls, env, company_id=None, scan_record=None, batch_size=500):
        """
        Executes a complete Revenue Guardian scan across all business rules.
        Guarantees idempotent upsert of risk cases via SHA-256 fingerprints.
        """
        start_time = datetime.datetime.now(datetime.timezone.utc)
        cid = company_id or (scan_record.company_id.id if scan_record and hasattr(scan_record.company_id, 'id') else 1)

        total_scanned = 0
        new_cases = 0
        updated_cases = 0
        errors = 0

        if scan_record:
            scan_record.write({'state': 'in_progress', 'start_time': start_time.isoformat()})

        rule_evaluators = [
            ('OVERDUE_INVOICE', RulesEngine.evaluate_overdue_invoices),
            ('EXPIRING_SUBSCRIPTION', RulesEngine.evaluate_expiring_subscriptions),
            ('EXPIRED_DISCOUNT', RulesEngine.evaluate_expired_discounts),
            ('UNMATCHED_PAYMENT', RulesEngine.evaluate_unmatched_payments),
            ('FAILED_PAYMENT', RulesEngine.evaluate_failed_payments),
        ]

        case_model = env['subscriptiq.risk.case']

        for rule_code, evaluator_fn in rule_evaluators:
            try:
                candidates = evaluator_fn(env, company_id=cid)
                total_scanned += len(candidates)

                for cand in candidates:
                    fp = cand['fingerprint']
                    # Look up existing active case by fingerprint
                    existing = case_model.search([('fingerprint', '=', fp)])
                    if existing:
                        # Update existing case details and amount
                        existing[0].write({
                            'amount_at_risk': cand['amount_at_risk'],
                            'severity': cand['severity'],
                            'risk_score': cand['risk_score'],
                            'explanation': cand['explanation'],
                            'last_checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
                        })
                        updated_cases += 1
                    else:
                        # Create new risk case
                        case_model.create({
                            'name': cand['name'],
                            'company_id': cand['company_id'],
                            'case_type': cand['case_type'],
                            'severity': cand['severity'],
                            'risk_score': cand['risk_score'],
                            'state': 'open',
                            'partner_id': cand.get('partner_id'),
                            'subscription_id': cand.get('subscription_id'),
                            'invoice_id': cand.get('invoice_id'),
                            'amount_at_risk': cand['amount_at_risk'],
                            'explanation': cand['explanation'],
                            'evidence': cand.get('evidence', ''),
                            'recommended_action': cand.get('recommended_action', ''),
                            'fingerprint': fp,
                            'detected_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
                        })
                        new_cases += 1

            except Exception as e:
                errors += 1
                _logger.exception("Error executing rule evaluator %s: %s", rule_code, str(e))

        end_time = datetime.datetime.now(datetime.timezone.utc)
        duration = (end_time - start_time).total_seconds()

        scan_result = {
            'records_scanned': total_scanned,
            'new_cases_found': new_cases,
            'cases_updated': updated_cases,
            'error_count': errors,
            'duration_seconds': duration,
            'state': 'completed' if errors == 0 else 'warning'
        }

        if scan_record:
            scan_record.write({
                'state': scan_result['state'],
                'end_time': end_time.isoformat(),
                'records_scanned': total_scanned,
                'cases_found': new_cases,
                'error_count': errors
            })

        _logger.info("Revenue Guardian scan complete: %s scanned, %s new cases, %s updated, in %.2fs",
                     total_scanned, new_cases, updated_cases, duration)

        return scan_result
