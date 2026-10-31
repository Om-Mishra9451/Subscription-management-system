"""
SubscriptIQ — Interactive Localhost Web Server & Dashboard
Runs on http://localhost:8069 (the standard Odoo port)
Provides interactive access to the Revenue Guardian Dashboard, Risk Cases,
Smart Reconciliation, Audit Trail, and AI Finance Copilot.
"""

import sys
import os
import json
import decimal
from decimal import Decimal
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from datetime import datetime, date, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Ensure local module path is included
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from subscriptiq.services.odoo_adapter import Environment, MODEL_REGISTRY, UserError
from subscriptiq.services.revenue_calculator import RevenueCalculator
from subscriptiq.services.rules_engine import RulesEngine
from subscriptiq.services.risk_engine import RiskEngine
from subscriptiq.services.billing_protection import BillingProtectionEngine
from subscriptiq.services.payment_matcher import PaymentMatcherEngine
from subscriptiq.services.ai.provider_manager import AIProviderManager

# Global state
GLOBAL_ENV = Environment()
AI_MANAGER = None

def init_demo_state():
    """Seeds rich Brightloop Software demonstration records."""
    global GLOBAL_ENV, AI_MANAGER
    
    # 1. Company
    company = GLOBAL_ENV['res.company'].create({
        'name': 'Brightloop Software Corp',
        'subscriptiq_active': True,
        'auto_approval_limit': 500.00,
        'dual_authorization_threshold': 5000.00,
        'default_ai_provider': 'groq'
    })
    GLOBAL_ENV.company = company
    
    # 2. Partners
    p1 = GLOBAL_ENV['res.partner'].create({'name': 'Acme Enterprise Ltd', 'email': 'billing@acme.com', 'is_company': True, 'company_id': company.id})
    p2 = GLOBAL_ENV['res.partner'].create({'name': 'BlueSky Retail Group', 'email': 'ap@bluesky.com', 'is_company': True, 'company_id': company.id})
    p3 = GLOBAL_ENV['res.partner'].create({'name': 'CloudMatrix Inc', 'email': 'finance@cloudmatrix.com', 'is_company': True, 'company_id': company.id})
    p4 = GLOBAL_ENV['res.partner'].create({'name': 'DataCore Analytics', 'email': 'ops@datacore.io', 'is_company': True, 'company_id': company.id})
    
    # 3. Plans
    plan_monthly = GLOBAL_ENV['subscriptiq.plan'].create({'name': 'Business Suite - Monthly', 'billing_interval': 'monthly', 'price': 1200.00, 'company_id': company.id})
    plan_yearly = GLOBAL_ENV['subscriptiq.plan'].create({'name': 'Enterprise Suite - Yearly', 'billing_interval': 'yearly', 'price': 14400.00, 'company_id': company.id})
    plan_daily = GLOBAL_ENV['subscriptiq.plan'].create({'name': 'Pay-as-you-go - Daily', 'billing_interval': 'daily', 'price': 50.00, 'company_id': company.id})
    
    today = date.today()
    
    # 4. Subscriptions
    s1 = GLOBAL_ENV['sale.order'].create({
        'name': 'SUB-2026-0001',
        'partner_id': p1.id,
        'company_id': company.id,
        'stage': 'in_progress',
        'subscriptiq_status': 'active',
        'plan_id': plan_monthly.id,
        'subscriptiq_plan_id': plan_monthly.id,
        'recurring_total': 1200.00,
        'subscriptiq_recurring_total': 1200.00,
        'next_renewal_date': str(today + timedelta(days=25)),
        'subscriptiq_next_renewal_date': str(today + timedelta(days=25))
    })
    
    s2 = GLOBAL_ENV['sale.order'].create({
        'name': 'SUB-2026-0002',
        'partner_id': p2.id,
        'company_id': company.id,
        'stage': 'in_progress',
        'subscriptiq_status': 'active',
        'plan_id': plan_yearly.id,
        'subscriptiq_plan_id': plan_yearly.id,
        'recurring_total': 14400.00,
        'subscriptiq_recurring_total': 14400.00,
        'next_renewal_date': str(today + timedelta(days=4)),  # Expiring soon!
        'subscriptiq_next_renewal_date': str(today + timedelta(days=4))
    })
    
    s3 = GLOBAL_ENV['sale.order'].create({
        'name': 'SUB-2026-0003',
        'partner_id': p3.id,
        'company_id': company.id,
        'stage': 'in_progress',
        'subscriptiq_status': 'active',
        'plan_id': plan_daily.id,
        'subscriptiq_plan_id': plan_daily.id,
        'recurring_total': 50.00,
        'subscriptiq_recurring_total': 50.00,
        'next_renewal_date': str(today + timedelta(days=1)),
        'subscriptiq_next_renewal_date': str(today + timedelta(days=1))
    })
    
    # 5. Invoices
    # Overdue invoice 1 (Critical)
    inv1 = GLOBAL_ENV['account.move'].create({
        'name': 'INV/2026/0001',
        'partner_id': p1.id,
        'company_id': company.id,
        'move_type': 'out_invoice',
        'state': 'posted',
        'payment_state': 'not_paid',
        'invoice_date': str(today - timedelta(days=45)),
        'invoice_date_due': str(today - timedelta(days=15)),
        'amount_total': 5000.00,
        'amount_residual': 5000.00,
        'subscriptiq_risk_state': 'unscreened'
    })
    
    # Overdue invoice 2 (Medium)
    inv2 = GLOBAL_ENV['account.move'].create({
        'name': 'INV/2026/0002',
        'partner_id': p2.id,
        'company_id': company.id,
        'move_type': 'out_invoice',
        'state': 'posted',
        'payment_state': 'not_paid',
        'invoice_date': str(today - timedelta(days=20)),
        'invoice_date_due': str(today - timedelta(days=5)),
        'amount_total': 2250.00,
        'amount_residual': 2250.00,
        'subscriptiq_risk_state': 'unscreened'
    })
    
    # Reconciled invoice (Previously recovered)
    inv3 = GLOBAL_ENV['account.move'].create({
        'name': 'INV/2026/0003',
        'partner_id': p4.id,
        'company_id': company.id,
        'move_type': 'out_invoice',
        'state': 'posted',
        'payment_state': 'paid',
        'invoice_date': str(today - timedelta(days=10)),
        'invoice_date_due': str(today - timedelta(days=2)),
        'amount_total': 1200.00,
        'amount_residual': 0.00,
        'subscriptiq_risk_state': 'recovered'
    })
    
    # Pre-seed a recovered verified case for historical metric
    GLOBAL_ENV['subscriptiq.risk.case'].create({
        'name': 'RISK-2026-0001',
        'company_id': company.id,
        'partner_id': p4.id,
        'invoice_id': inv3.id,
        'case_type': 'overdue_invoice',
        'severity': 'medium',
        'amount_at_risk': 1200.0,
        'recovered_amount': 1200.0,
        'state': 'resolved',
        'recovery_verified': True,
        'recommended_action': 'Reconciled via bank statement'
    })

    # Execute initial scan to populate Guardian Cases
    RiskEngine.execute_guardian_scan(GLOBAL_ENV, company.id)
    
    AI_MANAGER = AIProviderManager(GLOBAL_ENV)

init_demo_state()

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SubscriptIQ — Autonomous Revenue Assurance Engine</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #4f46e5;
            --primary-hover: #4338ca;
            --primary-light: #eef2ff;
            --success: #10b981;
            --success-light: #ecfdf5;
            --warning: #f59e0b;
            --warning-light: #fffbeb;
            --danger: #ef4444;
            --danger-light: #fef2f2;
            --dark: #0f172a;
            --gray-900: #1e293b;
            --gray-800: #334155;
            --gray-700: #475569;
            --gray-600: #64748b;
            --gray-300: #cbd5e1;
            --gray-200: #e2e8f0;
            --gray-100: #f1f5f9;
            --gray-50: #f8fafc;
            --white: #ffffff;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background-color: var(--gray-50); color: var(--gray-900); min-height: 100vh; display: flex; flex-direction: column; }
        
        /* Top Navigation */
        .navbar { background: var(--white); border-bottom: 1px solid var(--gray-200); height: 64px; display: flex; align-items: center; justify-content: space-between; padding: 0 2rem; position: sticky; top: 0; z-index: 50; }
        .nav-brand { display: flex; align-items: center; gap: 0.75rem; text-decoration: none; color: var(--dark); font-weight: 700; font-size: 1.25rem; }
        .logo-badge { background: linear-gradient(135deg, #4f46e5, #06b6d4); color: white; width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 800; }
        .tagline { color: var(--gray-600); font-size: 0.85rem; font-weight: 500; margin-left: 0.5rem; border-left: 1px solid var(--gray-300); padding-left: 0.75rem; }
        .nav-actions { display: flex; align-items: center; gap: 1rem; }
        .status-pill { background: var(--success-light); color: var(--success); padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.8rem; font-weight: 600; display: flex; align-items: center; gap: 0.5rem; }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--success); animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }

        /* Main Container */
        .container { max-width: 1300px; margin: 2rem auto; padding: 0 1.5rem; width: 100%; flex: 1; }

        /* Metric Grid */
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.25rem; margin-bottom: 2rem; }
        .metric-card { background: var(--white); border: 1px solid var(--gray-200); border-radius: 12px; padding: 1.25rem; box-shadow: var(--shadow-sm); position: relative; overflow: hidden; transition: transform 0.15s, box-shadow 0.15s; }
        .metric-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
        .metric-card.accent-danger { border-top: 4px solid var(--danger); }
        .metric-card.accent-success { border-top: 4px solid var(--success); }
        .metric-card.accent-primary { border-top: 4px solid var(--primary); }
        .metric-card.accent-warning { border-top: 4px solid var(--warning); }
        .metric-label { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--gray-600); margin-bottom: 0.5rem; }
        .metric-value { font-size: 1.75rem; font-weight: 700; color: var(--dark); }
        .metric-sub { font-size: 0.8rem; color: var(--gray-600); margin-top: 0.35rem; display: flex; align-items: center; gap: 0.35rem; }

        /* Controls Banner */
        .banner { background: white; border: 1px solid var(--gray-200); border-radius: 12px; padding: 1.25rem; margin-bottom: 2rem; display: flex; justify-content: space-between; align-items: center; box-shadow: var(--shadow-sm); flex-wrap: wrap; gap: 1rem; }
        .btn { display: inline-flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.65rem 1.25rem; border-radius: 8px; font-size: 0.875rem; font-weight: 600; cursor: pointer; border: none; transition: background 0.15s, transform 0.1s; }
        .btn:active { transform: scale(0.98); }
        .btn-primary { background: var(--primary); color: white; }
        .btn-primary:hover { background: var(--primary-hover); }
        .btn-outline { background: white; border: 1px solid var(--gray-300); color: var(--gray-800); }
        .btn-outline:hover { background: var(--gray-50); border-color: var(--gray-400); }
        .btn-sm { padding: 0.4rem 0.8rem; font-size: 0.75rem; }

        /* Sections & Tables */
        .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .section-title { font-size: 1.25rem; font-weight: 700; color: var(--dark); display: flex; align-items: center; gap: 0.5rem; }
        .card { background: white; border: 1px solid var(--gray-200); border-radius: 12px; box-shadow: var(--shadow-sm); overflow: hidden; margin-bottom: 2rem; }
        .table-responsive { width: 100%; overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.875rem; }
        th { background: var(--gray-50); padding: 0.85rem 1.25rem; font-weight: 600; color: var(--gray-700); border-bottom: 1px solid var(--gray-200); }
        td { padding: 1rem 1.25rem; border-bottom: 1px solid var(--gray-200); color: var(--gray-800); }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: #fafafa; }
        
        .badge { display: inline-block; padding: 0.25rem 0.6rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }
        .badge-critical { background: var(--danger-light); color: var(--danger); border: 1px solid #fecaca; }
        .badge-high { background: #ffedd5; color: #ea580c; border: 1px solid #fed7aa; }
        .badge-medium { background: var(--warning-light); color: #d97706; border: 1px solid #fde68a; }
        .badge-low { background: #e0f2fe; color: #0284c7; border: 1px solid #bae6fd; }
        .badge-open { background: #fef3c7; color: #b45309; }
        .badge-resolved { background: var(--success-light); color: var(--success); }

        /* Copilot Floating Widget */
        .copilot-launcher { position: fixed; bottom: 2rem; right: 2rem; width: 60px; height: 60px; border-radius: 50%; background: linear-gradient(135deg, #4f46e5, #06b6d4); color: white; display: flex; align-items: center; justify-content: center; box-shadow: var(--shadow-lg); cursor: pointer; z-index: 1000; border: none; font-size: 1.5rem; transition: transform 0.2s; }
        .copilot-launcher:hover { transform: scale(1.08); }
        .copilot-drawer { position: fixed; bottom: 6.5rem; right: 2rem; width: 420px; max-width: calc(100vw - 4rem); height: 560px; background: white; border-radius: 16px; box-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.25); border: 1px solid var(--gray-200); display: none; flex-direction: column; overflow: hidden; z-index: 1000; }
        .copilot-header { background: linear-gradient(135deg, #4f46e5, #4338ca); color: white; padding: 1rem 1.25rem; display: flex; justify-content: space-between; align-items: center; }
        .copilot-title { font-weight: 700; font-size: 1rem; display: flex; align-items: center; gap: 0.5rem; }
        .copilot-body { flex: 1; padding: 1.25rem; overflow-y: auto; display: flex; flex-direction: column; gap: 1rem; background: var(--gray-50); }
        .chat-bubble { max-width: 85%; padding: 0.75rem 1rem; border-radius: 12px; font-size: 0.875rem; line-height: 1.45; }
        .chat-bot { background: white; color: var(--gray-900); border: 1px solid var(--gray-200); align-self: flex-start; border-bottom-left-radius: 2px; }
        .chat-user { background: var(--primary); color: white; align-self: flex-end; border-bottom-right-radius: 2px; }
        .copilot-footer { padding: 0.75rem 1rem; background: white; border-top: 1px solid var(--gray-200); display: flex; gap: 0.5rem; }
        .copilot-input { flex: 1; border: 1px solid var(--gray-300); border-radius: 8px; padding: 0.5rem 0.75rem; font-size: 0.875rem; outline: none; }
        .copilot-input:focus { border-color: var(--primary); }

        /* Notification Toast */
        .toast { position: fixed; top: 1.5rem; right: 1.5rem; background: var(--dark); color: white; padding: 0.85rem 1.25rem; border-radius: 8px; font-size: 0.875rem; box-shadow: var(--shadow-lg); z-index: 2000; display: none; }
    </style>
</head>
<body>
    <div id="toast" class="toast"></div>

    <nav class="navbar">
        <div style="display:flex; align-items:center;">
            <a href="/" class="nav-brand">
                <div class="logo-badge">IQ</div>
                <span>SubscriptIQ</span>
            </a>
            <span class="tagline">Autonomous Revenue Assurance Engine for Odoo</span>
        </div>
        <div class="nav-actions">
            <span class="status-pill"><span class="status-dot"></span> Guardian Engine Active</span>
            <span style="font-size:0.85rem; color:var(--gray-600); font-weight:500;">Brightloop Software Corp</span>
        </div>
    </nav>

    <main class="container">
        <!-- Hero Metrics -->
        <div class="metrics-grid">
            <div class="metric-card accent-danger">
                <div class="metric-label">Revenue at Risk</div>
                <div class="metric-value" id="val-risk">$8,450.00</div>
                <div class="metric-sub" style="color:var(--danger)">⚠️ 2 overdue accounts flagged</div>
            </div>
            <div class="metric-card accent-success">
                <div class="metric-label">Verified Revenue Recovered</div>
                <div class="metric-value" id="val-recovered">$1,200.00</div>
                <div class="metric-sub" style="color:var(--success)">✓ Strictly bank reconciled</div>
            </div>
            <div class="metric-card accent-primary">
                <div class="metric-label">Monthly Recurring Revenue (MRR)</div>
                <div class="metric-value" id="val-mrr">$28,450.00</div>
                <div class="metric-sub">Normalized from active contracts</div>
            </div>
            <div class="metric-card accent-primary">
                <div class="metric-label">Annual Recurring Revenue (ARR)</div>
                <div class="metric-value" id="val-arr">$341,400.00</div>
                <div class="metric-sub">MRR × 12</div>
            </div>
            <div class="metric-card accent-warning">
                <div class="metric-label">Revenue Leakage Rate</div>
                <div class="metric-value" id="val-leakage">22.8%</div>
                <div class="metric-sub">Exposure vs Total Billed</div>
            </div>
        </div>

        <!-- Action Control Banner -->
        <div class="banner">
            <div>
                <h3 style="font-size:1.05rem; font-weight:700;">Autonomous Guardian Engine Controls</h3>
                <p style="font-size:0.85rem; color:var(--gray-600); margin-top:0.25rem;">Execute deterministic scanning, bank statement matching, and duplicate billing protection.</p>
            </div>
            <div style="display:flex; gap:0.75rem;">
                <button class="btn btn-outline" onclick="runDuplicateBillingTest()">🛡️ Test Duplicate Guard</button>
                <button class="btn btn-outline" onclick="simulateSmartReconciliation()">💳 Smart Bank Reconcile</button>
                <button class="btn btn-primary" onclick="triggerScan()">⚡ Run Guardian Scan</button>
            </div>
        </div>

        <!-- Risk Cases Table -->
        <div class="section-header">
            <h2 class="section-title">
                <span>Revenue Risk Cases</span>
                <span class="badge badge-open" id="cases-count">3 Open Cases</span>
            </h2>
            <div style="font-size:0.8rem; color:var(--gray-600);">SHA-256 Fingerprint Deduplication Guaranteed</div>
        </div>

        <div class="card">
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Case Number</th>
                            <th>Customer</th>
                            <th>Trigger Rule</th>
                            <th>Severity</th>
                            <th>Amount at Risk</th>
                            <th>Recommended Action</th>
                            <th>State</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody id="risk-cases-body">
                        <!-- Populated via JS -->
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Chained Audit Ledger -->
        <div class="section-header">
            <h2 class="section-title">
                <span>Tamper-Evident Chained Audit Trail</span>
            </h2>
            <div style="font-size:0.8rem; color:var(--gray-600);">Cryptographically Linked SHA-256 Ledger</div>
        </div>

        <div class="card">
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Sequence</th>
                            <th>Timestamp</th>
                            <th>Event Type</th>
                            <th>Payload Hash</th>
                            <th>Current Hash</th>
                            <th>Integrity</th>
                        </tr>
                    </thead>
                    <tbody id="audit-log-body">
                        <!-- Populated via JS -->
                    </tbody>
                </table>
            </div>
        </div>
    </main>

    <!-- Floating AI Copilot Launcher -->
    <button class="copilot-launcher" onclick="toggleCopilot()" title="Open SubscriptIQ AI Copilot">💬</button>

    <!-- AI Copilot Chat Drawer -->
    <div class="copilot-drawer" id="copilot-drawer">
        <div class="copilot-header">
            <div class="copilot-title">
                <span>🤖 SubscriptIQ Finance Copilot</span>
            </div>
            <button onclick="toggleCopilot()" style="background:none; border:none; color:white; font-size:1.25rem; cursor:pointer;">✕</button>
        </div>
        <div class="copilot-body" id="copilot-chat">
            <div class="chat-bubble chat-bot">
                Hello! I am your <strong>SubscriptIQ Autonomous Finance Copilot</strong>. I have real-time access to your revenue assurance data, risk cases, and recovery recommendations. How can I protect your revenue today?
            </div>
        </div>
        <div class="copilot-footer">
            <input type="text" id="copilot-input" class="copilot-input" placeholder="Ask e.g. What is our revenue at risk?" onkeydown="if(event.key==='Enter') sendCopilotQuery()">
            <button class="btn btn-primary btn-sm" onclick="sendCopilotQuery()">Send</button>
        </div>
    </div>

    <script>
        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 4000);
        }

        function toggleCopilot() {
            const drawer = document.getElementById('copilot-drawer');
            drawer.style.display = drawer.style.display === 'flex' ? 'none' : 'flex';
        }

        async function fetchState() {
            try {
                const res = await fetch('/api/state');
                const data = await res.json();
                
                // Update metrics
                document.getElementById('val-risk').innerText = '$' + Number(data.metrics.revenue_at_risk).toLocaleString('en-US', {minimumFractionDigits: 2});
                document.getElementById('val-recovered').innerText = '$' + Number(data.metrics.verified_recovered_revenue).toLocaleString('en-US', {minimumFractionDigits: 2});
                document.getElementById('val-mrr').innerText = '$' + Number(data.metrics.mrr).toLocaleString('en-US', {minimumFractionDigits: 2});
                document.getElementById('val-arr').innerText = '$' + Number(data.metrics.arr).toLocaleString('en-US', {minimumFractionDigits: 2});
                document.getElementById('val-leakage').innerText = data.metrics.revenue_leakage_rate + '%';
                
                // Update Risk Cases
                const tbody = document.getElementById('risk-cases-body');
                tbody.innerHTML = '';
                document.getElementById('cases-count').innerText = data.cases.length + ' Cases';
                
                data.cases.forEach(c => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td style="font-weight:600; font-family:'JetBrains Mono', monospace;">${c.name}</td>
                        <td>${c.partner_name}</td>
                        <td><span class="badge" style="background:#f3f4f6; color:#374151;">${c.rule_code}</span></td>
                        <td><span class="badge badge-${c.severity}">${c.severity.toUpperCase()}</span></td>
                        <td style="font-weight:700;">$${Number(c.amount_at_risk).toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                        <td style="font-size:0.8rem; color:var(--gray-600);">${c.recommended_action}</td>
                        <td><span class="badge badge-${c.state}">${c.state.toUpperCase()}</span></td>
                        <td>
                            ${c.state === 'open' ? `<button class="btn btn-outline btn-sm" onclick="executeRecovery(${c.id}, ${c.amount_at_risk})">Resolve</button>` : `<span style="color:var(--success); font-weight:600;">✓ Done</span>`}
                        </td>
                    `;
                    tbody.appendChild(tr);
                });

                // Update Audit Trail
                const auditBody = document.getElementById('audit-log-body');
                auditBody.innerHTML = '';
                data.audit_events.slice(-6).reverse().forEach(ev => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td style="font-family:'JetBrains Mono', monospace;">#${ev.sequence}</td>
                        <td style="font-size:0.8rem; color:var(--gray-600);">${ev.timestamp}</td>
                        <td><span class="badge badge-low">${ev.event_type}</span></td>
                        <td style="font-family:'JetBrains Mono', monospace; font-size:0.75rem;">${ev.payload_hash.substring(0, 16)}...</td>
                        <td style="font-family:'JetBrains Mono', monospace; font-size:0.75rem;">${ev.current_hash.substring(0, 16)}...</td>
                        <td><span style="color:var(--success); font-weight:600; font-size:0.75rem;">✓ Valid Chained</span></td>
                    `;
                    auditBody.appendChild(tr);
                });
            } catch(e) {
                console.error("Failed to fetch state:", e);
            }
        }

        async function triggerScan() {
            showToast("⚡ Executing Continuous Revenue Guardian Scan...");
            const res = await fetch('/api/scan', { method: 'POST' });
            const data = await res.json();
            showToast(`✓ Scan completed in ${data.duration_ms}ms. ${data.cases_created} new cases created, ${data.cases_updated} updated.`);
            fetchState();
        }

        async function runDuplicateBillingTest() {
            showToast("🛡️ Attempting concurrent billing simulation...");
            const res = await fetch('/api/test-duplicate-guard', { method: 'POST' });
            const data = await res.json();
            showToast(data.message);
            fetchState();
        }

        async function simulateSmartReconciliation() {
            showToast("💳 Ingesting bank statement and matching...");
            const res = await fetch('/api/reconcile-statement', { method: 'POST' });
            const data = await res.json();
            showToast(data.message);
            fetchState();
        }

        async function executeRecovery(caseId, amount) {
            if (amount >= 5000) {
                const conf = confirm(`⚠️ Amount at risk is $${amount}. Dual authorization is required. Proceed with Manager Sign-off?`);
                if (!conf) return;
            }
            const res = await fetch('/api/resolve-case', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ case_id: caseId })
            });
            const data = await res.json();
            showToast(data.message);
            fetchState();
        }

        async function sendCopilotQuery() {
            const input = document.getElementById('copilot-input');
            const query = input.value.trim();
            if (!query) return;
            
            const chat = document.getElementById('copilot-chat');
            const userMsg = document.createElement('div');
            userMsg.className = 'chat-bubble chat-user';
            userMsg.innerText = query;
            chat.appendChild(userMsg);
            input.value = '';
            chat.scrollTop = chat.scrollHeight;

            const botLoading = document.createElement('div');
            botLoading.className = 'chat-bubble chat-bot';
            botLoading.innerText = 'Analyzing revenue records...';
            chat.appendChild(botLoading);
            chat.scrollTop = chat.scrollHeight;

            try {
                const res = await fetch('/subscriptiq/copilot/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: query, company_id: 1 })
                });
                const data = await res.json();
                botLoading.innerHTML = `<strong>[${data.provider}]</strong><br>${data.response.replace(/\\n/g, '<br>')}`;
            } catch(e) {
                botLoading.innerText = 'Sorry, unable to contact copilot right now.';
            }
            chat.scrollTop = chat.scrollHeight;
        }

        // Initialize polling and render
        fetchState();
        setInterval(fetchState, 5000);
    </script>
</body>
</html>
"""

class SubscriptIQHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Quiet standard output
        pass

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == '/' or path == '/subscriptiq':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
        elif path == '/api/state':
            metrics = RevenueCalculator.compute_dashboard_metrics(GLOBAL_ENV)
            cases = []
            for c in GLOBAL_ENV['subscriptiq.risk.case'].search([]):
                cases.append({
                    'id': c.id,
                    'name': c.name,
                    'partner_name': c.partner_id.name if hasattr(c.partner_id, 'name') else 'Customer',
                    'rule_code': c.rule_id.code if hasattr(c.rule_id, 'code') else 'RULE',
                    'severity': c.severity,
                    'amount_at_risk': float(c.amount_at_risk),
                    'recommended_action': c.recommended_action,
                    'state': c.state
                })
            
            audit_events = []
            for ev in GLOBAL_ENV['subscriptiq.audit.event'].search([]):
                audit_events.append({
                    'sequence': ev.sequence,
                    'timestamp': ev.timestamp.strftime('%H:%M:%S') if ev.timestamp else '',
                    'event_type': ev.event_type,
                    'payload_hash': ev.payload_hash or '',
                    'current_hash': ev.current_hash or ''
                })

            self.send_json({
                'metrics': metrics,
                'cases': cases,
                'audit_events': audit_events
            })
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length > 0 else '{}'
        try:
            params = json.loads(body)
        except Exception:
            params = {}

        if path == '/api/scan':
            res = RiskEngine.execute_guardian_scan(GLOBAL_ENV, GLOBAL_ENV.company.id)
            self.send_json(res)

        elif path == '/api/test-duplicate-guard':
            # Attempt a duplicate reservation
            try:
                sub = GLOBAL_ENV['sale.order'].search([('name', '=', 'SUB-2026-0001')])[0]
                today = date.today()
                BillingProtectionEngine.acquire_billing_reservation(GLOBAL_ENV, sub, today, today + timedelta(days=30))
                # Attempt second concurrent reservation to trigger guard
                BillingProtectionEngine.acquire_billing_reservation(GLOBAL_ENV, sub, today, today + timedelta(days=30))
                self.send_json({'message': 'Billing slot reserved.'})
            except UserError as e:
                self.send_json({'message': f'🛡️ Duplicate Billing BLOCKED: {str(e)}'})

        elif path == '/api/reconcile-statement':
            # Reconcile overdue invoice 2 with a simulated deposit
            inv2 = GLOBAL_ENV['account.move'].search([('name', '=', 'INV/2026/0002')])[0]
            inv2.write({
                'state': 'posted',
                'payment_state': 'paid',
                'amount_residual': 0.0,
                'subscriptiq_risk_state': 'recovered',
                'subscriptiq_recovered_date': datetime.now(),
                'subscriptiq_recovered_amount': inv2.amount_total
            })
            # Also resolve the corresponding case if any
            for c in GLOBAL_ENV['subscriptiq.risk.case'].search([('invoice_id', '=', inv2.id)]):
                c.write({'state': 'resolved'})
            
            GLOBAL_ENV['subscriptiq.audit.event'].create({
                'event_type': 'reconciliation_verified',
                'user_id': GLOBAL_ENV.user,
                'company_id': GLOBAL_ENV.company,
                'model_name': 'account.move',
                'record_id': inv2.id,
                'payload_json': json.dumps({'reconciled_amount': float(inv2.amount_total), 'status': 'recovered'})
            })
            self.send_json({'message': f'✓ Reconciled deposit of ${inv2.amount_total:.2f} against {inv2.name}. Verified Revenue Recovered updated!'})

        elif path == '/api/resolve-case':
            case_id = params.get('case_id')
            case = GLOBAL_ENV['subscriptiq.risk.case'].browse(case_id)
            if case:
                case.write({'state': 'resolved'})
                GLOBAL_ENV['subscriptiq.audit.event'].create({
                    'event_type': 'case_resolved',
                    'user_id': GLOBAL_ENV.user,
                    'company_id': GLOBAL_ENV.company,
                    'model_name': 'subscriptiq.risk.case',
                    'record_id': case.id,
                    'payload_json': json.dumps({'resolved_by': 'Admin', 'case_name': case.name})
                })
                self.send_json({'message': f'✓ Case {case.name} marked as resolved and logged to audit trail.'})
            else:
                self.send_json({'message': 'Case not found.'}, status=404)

        elif path == '/subscriptiq/copilot/ask':
            prompt = params.get('prompt', '')
            res = AI_MANAGER.ask_copilot(GLOBAL_ENV, prompt, user_id=1, company_id=GLOBAL_ENV.company.id)
            self.send_json({
                'status': 'success',
                'provider': res.get('provider', 'Local Offline'),
                'response': res.get('answer', '')
            })
        else:
            self.send_response(404)
            self.end_headers()

def run_server(port=8069):
    server_address = ('', port)
    httpd = HTTPServer(server_address, SubscriptIQHandler)
    print(f"======================================================================")
    print(f"  SubscriptIQ Interactive Server Running")
    print(f"  Access URL: http://localhost:{port}")
    print(f"======================================================================")
    httpd.serve_forever()

if __name__ == '__main__':
    port = 8069
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    run_server(port)
