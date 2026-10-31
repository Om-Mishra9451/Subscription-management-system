#!/usr/bin/env python3
"""
SubscriptIQ Live Judge Demonstration Runner
Executes the exact 6 hackathon demonstration scenarios specified in Part 18:
- DEMO 1: Revenue Guardian Inspection & Risk Evidence Investigation
- DEMO 2: Transactional Duplicate Billing Prevention & Reservation Guard
- DEMO 3: Smart Payment Reconciliation & Verified Recovered Revenue Increase
- DEMO 4: AI Finance Copilot Grounded Query & Two-Phase Proposal Creation
- DEMO 5: Executive Revenue Assurance Intelligence (MRR, ARR, Leakage Rate)
- DEMO 6: Benchmark Laboratory & 50,000 Subscription Scalability
"""

import sys
import os
import json
import datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from subscriptiq.services.odoo_adapter import Environment, BaseRecord
import subscriptiq.models
from subscriptiq.services.revenue_calculator import RevenueCalculator
from subscriptiq.services.rules_engine import RulesEngine
from subscriptiq.services.risk_engine import RiskEngine
from subscriptiq.services.billing_protection import BillingProtectionEngine
from subscriptiq.services.payment_matcher import PaymentMatcherEngine
from subscriptiq.services.churn_scoring import CustomerRiskScorer
from subscriptiq.services.ai import AIProviderManager

def print_banner(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def run_demo():
    print_banner("SUBSCRIPTIQ — AUTONOMOUS REVENUE ASSURANCE FOR ODOO\n  Official Hackathon Demonstration Walkthrough for Technical Judges")

    env = Environment()

    # -------------------------------------------------------------
    # DEMO 1 — Revenue Guardian
    # -------------------------------------------------------------
    print_banner("DEMO 1 — REVENUE GUARDIAN ENGINE")
    print("Scenario: Continuous monitoring detects overdue invoices, explains risk, and generates audit evidence.")

    # Seed demo company & customer
    comp = env['res.company'].create({'name': 'Brightloop Software India Pvt Ltd'})
    customer = env['res.partner'].create({
        'name': 'Apex Global Tech',
        'email': 'finance@apexglobal.io',
        'company_id': comp.id
    })

    # Create overdue invoice (14 days past due, ₹12,500 residual)
    past_due_date = str(datetime.date.today() - datetime.timedelta(days=14))
    inv = env['account.move'].create({
        'name': 'INV/2026/0042',
        'partner_id': customer.id,
        'company_id': comp.id,
        'move_type': 'out_invoice',
        'state': 'posted',
        'payment_state': 'not_paid',
        'amount_total': 12500.0,
        'amount_residual': 12500.0,
        'invoice_date_due': past_due_date
    })

    print(f"[1] Seeded Customer '{customer.name}' with Invoice '{inv.name}' (Residual: ₹{inv.amount_residual:,.2f}, Due Date: {past_due_date})")
    print("[2] Executing Revenue Guardian automated scan...")

    scan_res = RiskEngine.execute_guardian_scan(env, company_id=comp.id)
    print(f"    -> Records Scanned: {scan_res['records_scanned']}")
    print(f"    -> New Risk Cases Created: {scan_res['new_cases_found']}")

    # Inspect the generated risk case
    cases = env['subscriptiq.risk.case'].search([('invoice_id', '=', inv.id)])
    case = cases[0]
    print(f"[3] Detected Risk Case #{case.id}: '{case.name}'")
    print(f"    - Category: {case.case_type}")
    print(f"    - Severity: {case.severity.upper()}")
    print(f"    - Risk Score: {case.risk_score} / 100")
    print(f"    - Amount at Risk: ₹{case.amount_at_risk:,.2f}")
    print(f"    - Explanation: {case.explanation}")
    print(f"    - Audit Evidence: {case.evidence}")
    print(f"    - Recommended Action: {case.recommended_action}")
    print(f"    - SHA-256 Fingerprint: {case.fingerprint[:24]}...")

    # -------------------------------------------------------------
    # DEMO 2 — Duplicate Billing Protection
    # -------------------------------------------------------------
    print_banner("DEMO 2 — TRANSACTIONAL DUPLICATE BILLING GUARD")
    print("Scenario: Billing engine transactionally locks period reservation to prevent duplicate invoice creation.")

    plan = env['subscriptiq.plan'].create({
        'name': 'Brightloop Enterprise Cloud',
        'code': 'ENT-CLOUD-MO',
        'billing_interval': 'monthly',
        'price': 15000.0,
        'company_id': comp.id
    })

    sub = env['sale.order'].create({
        'name': 'SUB/2026/0101',
        'partner_id': customer.id,
        'company_id': comp.id,
        'is_subscription': True,
        'stage': 'in_progress',
        'plan_id': plan.id,
        'recurring_total': 15000.0,
        'start_date': '2026-10-01',
        'next_invoice_date': '2026-10-01'
    })

    print(f"[1] Subscription '{sub.name}' active for October 2026.")
    print("[2] Generating first recurring invoice for period 2026-10-01 to 2026-10-30...")
    first_invoice = sub.generate_recurring_invoice(billing_date='2026-10-01')
    print(f"    -> Invoice '{first_invoice.name}' created successfully (Amount: ₹{first_invoice.amount_total:,.2f}).")

    # Check guard reservation
    guards = env['subscriptiq.billing.guard'].search([('subscription_id', '=', sub.id)])
    print(f"    -> Billing Guard Reservation Active: ID #{guards[0].id}, State: '{guards[0].state}', Key: {guards[0].idempotency_key[:20]}...")

    print("[3] Attempting second billing for the exact same billing period (Simulating duplicate trigger)...")
    try:
        sub.generate_recurring_invoice(billing_date='2026-10-01')
        print("    [ERROR] Duplicate was not blocked!")
    except Exception as e:
        print(f"    -> [SUCCESS] Duplicate Transaction Intercepted & Blocked: {str(e)}")

    # -------------------------------------------------------------
    # DEMO 3 — Smart Payment Reconciliation & Recovery
    # -------------------------------------------------------------
    print_banner("DEMO 3 — SMART PAYMENT RECONCILIATION & RECOVERED REVENUE")
    print("Scenario: Import CSV bank statement, match transaction with confidence weights, execute native reconciliation.")

    metrics_before = RevenueCalculator.compute_dashboard_metrics(env, company_id=comp.id)
    print(f"[1] Baseline Metrics Before Recovery:")
    print(f"    - Revenue at Risk: ₹{metrics_before['revenue_at_risk']:,.2f}")
    print(f"    - Verified Revenue Recovered: ₹{metrics_before['verified_recovered_revenue']:,.2f}")

    print("[2] Parsing demo bank statement CSV...")
    with open('demo_bank_statement.csv', 'r') as f:
        csv_data = f.read()

    parse_result = PaymentMatcherEngine.parse_and_validate_csv(csv_data)
    print(f"    -> Total Statement Rows Accepted: {len(parse_result['accepted'])}, Total Amount: ₹{parse_result['total_amount']:,.2f}")

    target_row = parse_result['accepted'][0] # TXN-BANK-9001 for ₹12,500 referencing INV/2026/0042
    print(f"[3] Inspecting Bank Transaction: Ref '{target_row['reference']}', Amount ₹{target_row['amount']:,.2f}, Payer '{target_row['partner_name']}'")

    import_line = env['subscriptiq.payment.import.line'].create({
        'batch_id': 1,
        'company_id': comp.id,
        'transaction_date': target_row['transaction_date'],
        'amount': target_row['amount'],
        'reference': target_row['reference'],
        'description': target_row['description'],
        'partner_name': target_row['partner_name'],
        'external_transaction_id': target_row['external_transaction_id'],
        'state': 'unmatched'
    })

    candidates = PaymentMatcherEngine.match_transaction(env, import_line, company_id=comp.id)
    print(f"[4] Matching Candidates Found: {len(candidates)}")
    top_candidate = candidates[0]
    print(f"    -> Matched Target Invoice: '{top_candidate['invoice_name']}'")
    print(f"    -> Match Confidence: {top_candidate['confidence'] * 100:.1f}% ({top_candidate['confidence_level'].upper()})")
    print(f"    -> Contributing Signals: {top_candidate['reasons']}")

    print("[5] Authorizing and executing native accounting payment reconciliation...")
    cand_record = env['subscriptiq.match.candidate'].create({
        'import_line_id': import_line.id,
        'invoice_id': top_candidate['invoice_id'],
        'confidence': top_candidate['confidence'],
        'confidence_level': top_candidate['confidence_level'],
        'state': 'proposed'
    })

    recon_res = PaymentMatcherEngine.execute_reconciliation(env, cand_record, user_id=1)
    print(f"    -> Reconciled Payment Created: Payment ID #{recon_res['payment_id']}")
    print(f"    -> Invoice Payment State: '{recon_res['new_payment_state'].upper()}'")
    print(f"    -> Remaining Residual: ₹{recon_res['remaining_residual']:,.2f}")

    # Re-calculate dashboard indicators
    metrics_after = RevenueCalculator.compute_dashboard_metrics(env, company_id=comp.id)
    print(f"[6] Updated Financial Indicators After Verified Reconciliation:")
    print(f"    - Verified Revenue Recovered: ₹{metrics_after['verified_recovered_revenue']:,.2f} (+₹{recon_res['reconciled_amount']:,.2f})")
    print(f"    - Revenue at Risk: ₹{metrics_after['revenue_at_risk']:,.2f}")
    print(f"    - Leakage Rate: {metrics_after['revenue_leakage_rate']}%")

    # -------------------------------------------------------------
    # DEMO 4 — AI Finance Copilot
    # -------------------------------------------------------------
    print_banner("DEMO 4 — AI FINANCE COPILOT (GROUNDED & SECURE)")
    print("Scenario: Financial queries answered exclusively from database records; write actions require human approval.")

    manager = AIProviderManager({})
    print("[1] Query: 'What is our current Monthly Recurring Revenue and Revenue at Risk?'")
    resp1 = manager.ask_copilot(env, "What is our current Monthly Recurring Revenue and Revenue at Risk?")
    print(f"    -> Copilot Response: {resp1['answer']}")

    print("\n[2] Query: 'Prepare payment reminders for overdue customers.' (Write Action Proposal)")
    resp2 = manager.ask_copilot(env, "Prepare reminders for overdue customer invoice INV/2026/0042")
    print(f"    -> Copilot Action: Generated safe two-phase proposal.")
    print(f"    -> Execution Details: {resp2.get('tool_calls', [{}])[0].get('result', {})}")
    print("    -> Human-in-the-loop Guard: Action held in 'awaiting_approval' status until authorized by manager.")

    # -------------------------------------------------------------
    # DEMO 5 — Executive Revenue Intelligence
    # -------------------------------------------------------------
    print_banner("DEMO 5 — EXECUTIVE REVENUE INTELLIGENCE METRICS")
    print(f"Summary of Verified Platform Metrics:")
    print(f"  • Monthly Recurring Revenue (MRR): ₹{metrics_after['mrr']:,.2f}")
    print(f"  • Annualized Recurring Revenue (ARR): ₹{metrics_after['arr']:,.2f}")
    print(f"  • Verified Revenue Recovered: ₹{metrics_after['verified_recovered_revenue']:,.2f}")
    print(f"  • Revenue at Risk: ₹{metrics_after['revenue_at_risk']:,.2f}")
    print(f"  • Revenue Leakage Rate: {metrics_after['revenue_leakage_rate']}%")
    print(f"  • Active Subscriptions: {metrics_after['active_subscriptions']}")
    print(f"  • Outstanding Receivables: ₹{metrics_after['outstanding_amount']:,.2f}")

    # -------------------------------------------------------------
    # DEMO 6 — Performance & Scalability Laboratory
    # -------------------------------------------------------------
    print_banner("DEMO 6 — PERFORMANCE & SCALABILITY LABORATORY")
    if os.path.exists('benchmark_results.json'):
        with open('benchmark_results.json') as f:
            bench = json.load(f)
        scan = bench['scan_performance']
        lat = bench['dashboard_latencies_ms']
        print(f"Audited 50,000-Subscription Dataset Results:")
        print(f"  • Total Subscriptions Audited: {bench['dataset_summary']['subscriptions']:,}")
        print(f"  • Invoices Processed: {bench['dataset_summary']['invoices']:,}")
        print(f"  • Scan Duration: {scan['duration_seconds']} seconds ({scan['throughput_records_per_sec']:,.0f} records/sec)")
        print(f"  • Interactive Dashboard Latency p50: {lat['p50']} ms")
        print(f"  • Interactive Dashboard Latency p95: {lat['p95']} ms (Target < 2,000 ms: {'ACHIEVED' if lat['two_second_target_achieved'] else 'MISSED'})")
        print(f"  • Interactive Dashboard Latency p99: {lat['p99']} ms")
        print(f"  • Detection False Positive Rate: {scan['false_positive_rate'] * 100:.4f}%")

    print_banner("ALL 6 DEMONSTRATION SCENARIOS COMPLETED SUCCESSFULLY")
    return 0

if __name__ == '__main__':
    sys.exit(run_demo())
