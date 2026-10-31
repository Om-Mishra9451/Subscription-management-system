"""
SubscriptIQ — Complete Subscription Management System & Revenue Assurance Engine
Implements ALL 5 Original Challenge Modules + Revenue Guardian + AI Copilot:
- Module 1: User Management & Access Control (Admin, Staff, Customer, Password Complexity, Reset)
- Module 2: Product & Plan Configuration (Variants with Surcharges, Daily Recurrence, Discounts, Taxes)
- Module 3: Quotation & Subscription Workflow (Templates, Draft -> Quotation -> Confirmed -> Active -> Closed)
- Module 4: Automated Billing & Payments (Recurring Engine, Duplicate Guard, Partial/Full Payments, Settlement)
- Module 5: Business Reporting & Finance Dashboard (10 KPIs, Multi-Attribute Filters, 7 Business Visualizations)
- Integrated SubscriptIQ Features: Revenue Guardian, SHA-256 Audit Trail, Smart Reconciliation, Copilot
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

from subscriptiq.services.odoo_adapter import Environment, MODEL_REGISTRY, UserError, ValidationError
import subscriptiq.models # Register all models
from subscriptiq.models.user_management import ResUsers
from subscriptiq.services.revenue_calculator import RevenueCalculator
from subscriptiq.services.rules_engine import RulesEngine
from subscriptiq.services.risk_engine import RiskEngine
from subscriptiq.services.billing_protection import BillingProtectionEngine
from subscriptiq.services.billing_engine import BillingEngine
from subscriptiq.services.payment_matcher import PaymentMatcherEngine
from subscriptiq.services.ai.provider_manager import AIProviderManager

# Global state
GLOBAL_ENV = Environment()
AI_MANAGER = None

def init_master_database():
    """Initializes comprehensive Brightloop Software seed database covering all 5 modules."""
    global GLOBAL_ENV, AI_MANAGER
    GLOBAL_ENV = Environment()
    today = date.today()

    # 1. Company
    company = GLOBAL_ENV['res.company'].create({
        'name': 'Brightloop Software Corp',
        'subscriptiq_active': True,
        'auto_approval_limit': 500.00,
        'dual_authorization_threshold': 5000.00,
        'default_ai_provider': 'gemini'
    })
    GLOBAL_ENV.company = company

    # -------------------------------------------------------------
    # MODULE 1 SEED: USERS & ROLES
    # -------------------------------------------------------------
    admin_user = ResUsers.create_user(GLOBAL_ENV, {
        'name': 'Chief Administrator',
        'login': 'admin@brightloop.software',
        'password': 'SuperAdmin@2026',
        'role': 'admin'
    })
    GLOBAL_ENV.user = admin_user

    staff_user = ResUsers.create_user(GLOBAL_ENV, {
        'name': 'Operations Staff',
        'login': 'staff@brightloop.software',
        'password': 'StaffMember@2026',
        'role': 'staff'
    })

    cust1_partner = GLOBAL_ENV['res.partner'].create({'name': 'Acme Enterprise Ltd', 'email': 'billing@acme.com', 'is_company': True})
    cust1_user = ResUsers.create_user(GLOBAL_ENV, {
        'name': 'Alice Manager',
        'login': 'alice@acme.com',
        'password': 'CustomerP@ss2026',
        'role': 'customer',
        'partner_id': cust1_partner.id
    })

    cust2_partner = GLOBAL_ENV['res.partner'].create({'name': 'BlueSky Retail Group', 'email': 'ap@bluesky.com', 'is_company': True})
    cust3_partner = GLOBAL_ENV['res.partner'].create({'name': 'CloudMatrix Inc', 'email': 'finance@cloudmatrix.com', 'is_company': True})
    cust4_partner = GLOBAL_ENV['res.partner'].create({'name': 'DataCore Analytics', 'email': 'ops@datacore.io', 'is_company': True})

    # -------------------------------------------------------------
    # MODULE 2 SEED: PRODUCTS, VARIANTS, PLANS, DISCOUNTS, TAXES
    # -------------------------------------------------------------
    # Base Product & Variants (Original Hackathon Example: ₹1,000 base + ₹560 Odoo Brand = ₹1,560)
    tmpl_software = GLOBAL_ENV['product.template'].create({
        'name': 'Business Software',
        'product_type': 'service',
        'list_price': 1000.00,
        'standard_price': 400.00,
        'description': 'Brightloop Core Business Cloud Software'
    })
    attr_brand = GLOBAL_ENV['product.attribute'].create({'name': 'Brand Edition'})
    val_default = GLOBAL_ENV['product.attribute.value'].create({'name': 'Default', 'attribute_id': attr_brand.id, 'price_extra': 0.0})
    val_odoo = GLOBAL_ENV['product.attribute.value'].create({'name': 'Odoo Brand', 'attribute_id': attr_brand.id, 'price_extra': 560.0})

    var_default = GLOBAL_ENV['product.product'].create({
        'product_tmpl_id': tmpl_software.id,
        'attribute_value_ids': [val_default.id],
        'price_extra': 0.0
    })
    var_odoo = GLOBAL_ENV['product.product'].create({
        'product_tmpl_id': tmpl_software.id,
        'attribute_value_ids': [val_odoo.id],
        'price_extra': 560.0
    })

    tmpl_addon = GLOBAL_ENV['product.template'].create({
        'name': 'API Connector Add-on',
        'product_type': 'service',
        'list_price': 250.00,
        'standard_price': 50.00,
        'description': 'High-volume external API gateway connector'
    })

    # Taxes
    tax_gst = GLOBAL_ENV['account.tax'].create({
        'name': 'GST 18%',
        'amount_type': 'percent',
        'amount': 18.0,
        'price_include': False
    })

    # Plans (Daily, Weekly, Monthly, Yearly)
    plan_daily = GLOBAL_ENV['subscriptiq.plan'].create({
        'name': 'Pay-as-you-go - Daily',
        'billing_interval': 'daily',
        'price': 50.00,
        'pause_policy': 'allowed',
        'early_closure_policy': 'allowed'
    })
    plan_monthly = GLOBAL_ENV['subscriptiq.plan'].create({
        'name': 'Business Suite - Monthly',
        'billing_interval': 'monthly',
        'price': 1200.00,
        'pause_policy': 'allowed',
        'early_closure_policy': 'allowed'
    })
    plan_yearly = GLOBAL_ENV['subscriptiq.plan'].create({
        'name': 'Enterprise Suite - Yearly',
        'billing_interval': 'yearly',
        'price': 14400.00,
        'pause_policy': 'allowed',
        'early_closure_policy': 'disallowed'
    })

    # Discounts
    disc_promo = GLOBAL_ENV['subscriptiq.discount'].create({
        'name': 'New Customer 15% Off',
        'code': 'WELCOME15',
        'discount_type': 'percentage',
        'value': 15.0,
        'min_purchase_amount': 500.0,
        'start_date': str(today - timedelta(days=10)),
        'end_date': str(today + timedelta(days=60)),
        'max_usage_limit': 100,
        'scope': 'entire_subscription'
    })

    # -------------------------------------------------------------
    # MODULE 3 SEED: QUOTATION TEMPLATES & SUBSCRIPTIONS
    # -------------------------------------------------------------
    # Quotation Template
    q_template = GLOBAL_ENV['sale.order.template'].create({
        'name': 'Standard Enterprise Onboarding',
        'plan_id': plan_monthly.id,
        'number_of_days': 30,
        'note': 'Standard terms: 30-day billing, automatic monthly renewal.'
    })

    # Quotation in Draft
    q1 = GLOBAL_ENV['sale.order'].create({
        'name': 'SO-QUOTE-2026-001',
        'partner_id': cust4_partner.id,
        'company_id': company.id,
        'subscriptiq_plan_id': plan_monthly.id,
        'subscriptiq_status': 'quotation',
        'state': 'sent',
        'subscriptiq_recurring_total': 1200.00,
        'amount_total': 1416.00
    })

    # Active Subscriptions with Mandatory Lifecycle
    sub1 = GLOBAL_ENV['sale.order'].create({
        'name': 'SUB-2026-0001',
        'partner_id': cust1_partner.id,
        'company_id': company.id,
        'subscriptiq_status': 'active',
        'stage': 'in_progress',
        'subscriptiq_plan_id': plan_monthly.id,
        'plan_id': plan_monthly.id,
        'subscriptiq_recurring_total': 1200.00,
        'recurring_total': 1200.00,
        'subscriptiq_next_renewal_date': str(today + timedelta(days=20)),
        'next_renewal_date': str(today + timedelta(days=20))
    })

    sub2 = GLOBAL_ENV['sale.order'].create({
        'name': 'SUB-2026-0002',
        'partner_id': cust2_partner.id,
        'company_id': company.id,
        'subscriptiq_status': 'active',
        'stage': 'in_progress',
        'subscriptiq_plan_id': plan_yearly.id,
        'plan_id': plan_yearly.id,
        'subscriptiq_recurring_total': 14400.00,
        'recurring_total': 14400.00,
        'subscriptiq_next_renewal_date': str(today + timedelta(days=4)), # Expiring soon!
        'next_renewal_date': str(today + timedelta(days=4))
    })

    sub3 = GLOBAL_ENV['sale.order'].create({
        'name': 'SUB-2026-0003',
        'partner_id': cust3_partner.id,
        'company_id': company.id,
        'subscriptiq_status': 'active',
        'stage': 'in_progress',
        'subscriptiq_plan_id': plan_daily.id,
        'plan_id': plan_daily.id,
        'subscriptiq_recurring_total': 50.00,
        'recurring_total': 50.00,
        'subscriptiq_next_renewal_date': str(today), # Due for billing today!
        'next_renewal_date': str(today)
    })

    # Paused Subscription
    sub4 = GLOBAL_ENV['sale.order'].create({
        'name': 'SUB-2026-0004',
        'partner_id': cust4_partner.id,
        'company_id': company.id,
        'subscriptiq_status': 'paused',
        'stage': 'paused',
        'subscriptiq_plan_id': plan_monthly.id,
        'subscriptiq_recurring_total': 1200.00
    })

    # -------------------------------------------------------------
    # MODULE 4 SEED: INVOICES & PAYMENTS
    # -------------------------------------------------------------
    # 1. Overdue Invoice (Critical)
    inv1 = GLOBAL_ENV['account.move'].create({
        'name': 'INV/2026/0001',
        'partner_id': cust1_partner.id,
        'company_id': company.id,
        'move_type': 'out_invoice',
        'state': 'posted',
        'payment_state': 'not_paid',
        'invoice_date': str(today - timedelta(days=45)),
        'invoice_date_due': str(today - timedelta(days=15)), # 15 days overdue
        'amount_total': 5000.00,
        'amount_residual': 5000.00,
        'subscriptiq_risk_state': 'unscreened'
    })

    # 2. Overdue Invoice with Partial Payment (Medium)
    inv2 = GLOBAL_ENV['account.move'].create({
        'name': 'INV/2026/0002',
        'partner_id': cust2_partner.id,
        'company_id': company.id,
        'move_type': 'out_invoice',
        'state': 'posted',
        'payment_state': 'not_paid',
        'invoice_date': str(today - timedelta(days=20)),
        'invoice_date_due': str(today - timedelta(days=5)), # 5 days overdue
        'amount_total': 2250.00,
        'amount_residual': 1250.00, # 1,000 partially paid
        'subscriptiq_risk_state': 'unscreened'
    })
    # Partial payment record
    GLOBAL_ENV['account.payment'].create({
        'name': 'PAY/2026/0001',
        'partner_id': cust2_partner.id,
        'company_id': company.id,
        'invoice_id': inv2.id,
        'payment_method': 'bank_transfer',
        'amount': 1000.00,
        'payment_date': str(today - timedelta(days=18)),
        'transaction_reference': 'WIRE-AC-9941',
        'state': 'posted'
    })

    # 3. Fully Settled & Reconciled Invoice
    inv3 = GLOBAL_ENV['account.move'].create({
        'name': 'INV/2026/0003',
        'partner_id': cust4_partner.id,
        'company_id': company.id,
        'move_type': 'out_invoice',
        'state': 'posted',
        'payment_state': 'paid',
        'invoice_date': str(today - timedelta(days=10)),
        'invoice_date_due': str(today - timedelta(days=2)),
        'amount_total': 1200.00,
        'amount_residual': 0.00,
        'subscriptiq_risk_state': 'recovered',
        'subscriptiq_recovered_date': datetime.now(),
        'subscriptiq_recovered_amount': 1200.00
    })
    GLOBAL_ENV['account.payment'].create({
        'name': 'PAY/2026/0002',
        'partner_id': cust4_partner.id,
        'company_id': company.id,
        'invoice_id': inv3.id,
        'payment_method': 'credit_card',
        'amount': 1200.00,
        'payment_date': str(today - timedelta(days=5)),
        'transaction_reference': 'CARD-AUTH-8812',
        'state': 'posted'
    })

    # Pre-seed verified case for recovered metric
    GLOBAL_ENV['subscriptiq.risk.case'].create({
        'name': 'RISK-2026-0001',
        'company_id': company.id,
        'partner_id': cust4_partner.id,
        'invoice_id': inv3.id,
        'case_type': 'overdue_invoice',
        'severity': 'medium',
        'amount_at_risk': 1200.0,
        'recovered_amount': 1200.0,
        'state': 'resolved',
        'recovery_verified': True,
        'recommended_action': 'Reconciled via bank statement'
    })

    # Initial Revenue Guardian scan
    RiskEngine.execute_guardian_scan(GLOBAL_ENV, company.id)
    AI_MANAGER = AIProviderManager(GLOBAL_ENV)

init_master_database()

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Brightloop — Subscription Management & Revenue Assurance System</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
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
        .nav-brand { display: flex; align-items: center; gap: 0.75rem; text-decoration: none; color: var(--dark); font-weight: 800; font-size: 1.25rem; }
        .logo-badge { background: linear-gradient(135deg, #4f46e5, #06b6d4); color: white; width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 800; }
        .tagline { color: var(--gray-600); font-size: 0.85rem; font-weight: 500; margin-left: 0.5rem; border-left: 1px solid var(--gray-300); padding-left: 0.75rem; }
        .nav-actions { display: flex; align-items: center; gap: 0.75rem; }
        
        /* Main Navigation Tabs */
        .module-nav { background: var(--white); border-bottom: 1px solid var(--gray-200); padding: 0 2rem; display: flex; gap: 0.5rem; overflow-x: auto; }
        .nav-tab { padding: 0.9rem 1.25rem; font-size: 0.875rem; font-weight: 600; color: var(--gray-600); border-bottom: 3px solid transparent; cursor: pointer; display: flex; align-items: center; gap: 0.5rem; white-space: nowrap; transition: color 0.15s, border-color 0.15s; }
        .nav-tab:hover { color: var(--primary); }
        .nav-tab.active { color: var(--primary); border-bottom-color: var(--primary); }

        /* Container */
        .container { max-width: 1350px; margin: 1.5rem auto; padding: 0 1.5rem; width: 100%; flex: 1; }
        .tab-content { display: none; }
        .tab-content.active { display: block; animation: fadeIn 0.2s ease-in; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

        /* Metric Grid */
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
        .metric-card { background: var(--white); border: 1px solid var(--gray-200); border-radius: 12px; padding: 1.25rem; box-shadow: var(--shadow-sm); position: relative; overflow: hidden; }
        .metric-card.accent-danger { border-top: 4px solid var(--danger); }
        .metric-card.accent-success { border-top: 4px solid var(--success); }
        .metric-card.accent-primary { border-top: 4px solid var(--primary); }
        .metric-card.accent-warning { border-top: 4px solid var(--warning); }
        .metric-label { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--gray-600); margin-bottom: 0.4rem; }
        .metric-value { font-size: 1.6rem; font-weight: 800; color: var(--dark); }
        .metric-sub { font-size: 0.8rem; color: var(--gray-600); margin-top: 0.35rem; }

        /* Card & Tables */
        .card { background: white; border: 1px solid var(--gray-200); border-radius: 12px; box-shadow: var(--shadow-sm); overflow: hidden; margin-bottom: 1.5rem; }
        .card-header { padding: 1rem 1.25rem; border-bottom: 1px solid var(--gray-200); display: flex; justify-content: space-between; align-items: center; background: white; }
        .card-title { font-size: 1.1rem; font-weight: 700; color: var(--dark); display: flex; align-items: center; gap: 0.5rem; }
        .table-responsive { width: 100%; overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.875rem; }
        th { background: var(--gray-50); padding: 0.75rem 1rem; font-weight: 600; color: var(--gray-700); border-bottom: 1px solid var(--gray-200); }
        td { padding: 0.85rem 1rem; border-bottom: 1px solid var(--gray-200); color: var(--gray-800); }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: #fafafa; }

        /* Buttons & Controls */
        .btn { display: inline-flex; align-items: center; justify-content: center; gap: 0.4rem; padding: 0.6rem 1rem; border-radius: 8px; font-size: 0.85rem; font-weight: 600; cursor: pointer; border: none; transition: background 0.15s, transform 0.1s; }
        .btn:active { transform: scale(0.98); }
        .btn-primary { background: var(--primary); color: white; }
        .btn-primary:hover { background: var(--primary-hover); }
        .btn-outline { background: white; border: 1px solid var(--gray-300); color: var(--gray-800); }
        .btn-outline:hover { background: var(--gray-50); border-color: var(--gray-400); }
        .btn-success { background: var(--success); color: white; }
        .btn-sm { padding: 0.35rem 0.65rem; font-size: 0.75rem; }

        /* Badges */
        .badge { display: inline-block; padding: 0.2rem 0.55rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }
        .badge-active { background: var(--success-light); color: var(--success); border: 1px solid #a7f3d0; }
        .badge-draft { background: #f3f4f6; color: #4b5563; }
        .badge-quotation { background: #e0f2fe; color: #0369a1; }
        .badge-confirmed { background: #fef3c7; color: #b45309; }
        .badge-paused { background: #fed7aa; color: #c2410c; }
        .badge-closed { background: #f1f5f9; color: #64748b; }
        .badge-critical { background: var(--danger-light); color: var(--danger); border: 1px solid #fecaca; }
        .badge-high { background: #ffedd5; color: #ea580c; border: 1px solid #fed7aa; }
        .badge-medium { background: var(--warning-light); color: #d97706; border: 1px solid #fde68a; }
        .badge-low { background: #e0f2fe; color: #0284c7; }

        /* Form Modal */
        .modal { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(15,23,42,0.6); z-index:2000; align-items:center; justify-content:center; }
        .modal-card { background:white; border-radius:12px; width:92%; max-width:650px; max-height:90vh; display:flex; flex-direction:column; overflow:hidden; box-shadow:var(--shadow-lg); }
        .modal-header { padding:1rem 1.25rem; background:var(--gray-900); color:white; display:flex; justify-content:space-between; align-items:center; }
        .modal-body { padding:1.25rem; overflow-y:auto; display:flex; flex-direction:column; gap:1rem; }
        .modal-footer { padding:1rem 1.25rem; background:var(--gray-50); border-top:1px solid var(--gray-200); display:flex; justify-content:flex-end; gap:0.75rem; }
        .form-group { display:flex; flex-direction:column; gap:0.35rem; }
        .form-label { font-size:0.8rem; font-weight:600; color:var(--gray-700); }
        .form-input, .form-select, .form-textarea { width:100%; border:1px solid var(--gray-300); border-radius:8px; padding:0.55rem 0.75rem; font-size:0.875rem; outline:none; }
        .form-input:focus, .form-select:focus, .form-textarea:focus { border-color:var(--primary); }

        /* Copilot Floating Widget */
        .copilot-launcher { position: fixed; bottom: 2rem; right: 2rem; width: 60px; height: 60px; border-radius: 50%; background: linear-gradient(135deg, #4f46e5, #06b6d4); color: white; display: flex; align-items: center; justify-content: center; box-shadow: var(--shadow-lg); cursor: pointer; z-index: 1000; border: none; font-size: 1.5rem; transition: transform 0.2s; }
        .copilot-launcher:hover { transform: scale(1.08); }
        .copilot-drawer { position: fixed; bottom: 6.5rem; right: 2rem; width: 420px; max-width: calc(100vw - 4rem); height: 560px; background: white; border-radius: 16px; box-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.25); border: 1px solid var(--gray-200); display: none; flex-direction: column; overflow: hidden; z-index: 1000; }
        .copilot-header { background: linear-gradient(135deg, #4f46e5, #4338ca); color: white; padding: 1rem 1.25rem; display: flex; justify-content: space-between; align-items: center; }
        .copilot-body { flex: 1; padding: 1.25rem; overflow-y: auto; display: flex; flex-direction: column; gap: 1rem; background: var(--gray-50); }
        .chat-bubble { max-width: 85%; padding: 0.75rem 1rem; border-radius: 12px; font-size: 0.875rem; line-height: 1.45; }
        .chat-bot { background: white; color: var(--gray-900); border: 1px solid var(--gray-200); align-self: flex-start; }
        .chat-user { background: var(--primary); color: white; align-self: flex-end; }
        .copilot-footer { padding: 0.75rem 1rem; background: white; border-top: 1px solid var(--gray-200); display: flex; gap: 0.5rem; }

        /* Toast */
        .toast { position: fixed; top: 1.5rem; right: 1.5rem; background: var(--dark); color: white; padding: 0.85rem 1.25rem; border-radius: 8px; font-size: 0.875rem; box-shadow: var(--shadow-lg); z-index: 3000; display: none; }
    </style>
</head>
<body>
    <div id="toast" class="toast"></div>

    <!-- Header -->
    <nav class="navbar">
        <div style="display:flex; align-items:center;">
            <a href="/" class="nav-brand">
                <div class="logo-badge">BL</div>
                <span>Brightloop</span>
            </a>
            <span class="tagline">Subscription Management & Autonomous Revenue Assurance System</span>
        </div>
        <div class="nav-actions">
            <button class="btn btn-outline btn-sm" onclick="toggleDbExplorer()">🗄️ Database Tables</button>
            <span class="badge badge-active">● System Live</span>
            <span style="font-size:0.85rem; color:var(--gray-600); font-weight:600;">Admin Mode</span>
        </div>
    </nav>

    <!-- Top Tabs (5 Core Modules + Revenue Guardian) -->
    <nav class="module-nav">
        <div class="nav-tab active" onclick="switchTab('tab-finance')">📊 1. Business Finance Dashboard (Module 5)</div>
        <div class="nav-tab" onclick="switchTab('tab-users')">👥 2. User Management & RBAC (Module 1)</div>
        <div class="nav-tab" onclick="switchTab('tab-products')">📦 3. Products & Plans (Module 2)</div>
        <div class="nav-tab" onclick="switchTab('tab-subs')">📑 4. Quotations & Subscriptions (Module 3)</div>
        <div class="nav-tab" onclick="switchTab('tab-billing')">💳 5. Billing & Payments (Module 4)</div>
        <div class="nav-tab" onclick="switchTab('tab-guardian')">🛡️ Revenue Guardian & Assurance</div>
    </nav>

    <main class="container">
        <!-- ============================================================= -->
        <!-- TAB 1: MODULE 5 — BUSINESS FINANCE DASHBOARD                   -->
        <!-- ============================================================= -->
        <section id="tab-finance" class="tab-content active">
            <!-- 10 Key Indicators -->
            <div class="metrics-grid">
                <div class="metric-card accent-primary">
                    <div class="metric-label">Active Subscriptions</div>
                    <div class="metric-value" id="fin-active-subs">-</div>
                    <div class="metric-sub">Active paying contracts</div>
                </div>
                <div class="metric-card accent-primary">
                    <div class="metric-label">Total Recurring Revenue</div>
                    <div class="metric-value" id="fin-recurring-rev">-</div>
                    <div class="metric-sub">Contracted billing run</div>
                </div>
                <div class="metric-card accent-success">
                    <div class="metric-label">Monthly Recurring Revenue (MRR)</div>
                    <div class="metric-value" id="fin-mrr">-</div>
                    <div class="metric-sub">Normalized monthly basis</div>
                </div>
                <div class="metric-card accent-success">
                    <div class="metric-label">Annual Recurring Revenue (ARR)</div>
                    <div class="metric-value" id="fin-arr">-</div>
                    <div class="metric-sub">MRR × 12</div>
                </div>
                <div class="metric-card accent-primary">
                    <div class="metric-label">Revenue Received</div>
                    <div class="metric-value" id="fin-rev-received">-</div>
                    <div class="metric-sub">Actual settled cash</div>
                </div>
                <div class="metric-card accent-warning">
                    <div class="metric-label">Outstanding Amount</div>
                    <div class="metric-value" id="fin-outstanding">-</div>
                    <div class="metric-sub">Unpaid invoice residuals</div>
                </div>
                <div class="metric-card accent-danger">
                    <div class="metric-label">Overdue Invoices Amount</div>
                    <div class="metric-value" id="fin-overdue">-</div>
                    <div class="metric-sub">Receivables past due date</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Total Invoices Billed</div>
                    <div class="metric-value" id="fin-total-inv">-</div>
                    <div class="metric-sub">Customer invoices</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Total Customers</div>
                    <div class="metric-value" id="fin-total-cust">-</div>
                    <div class="metric-sub">Corporate accounts</div>
                </div>
                <div class="metric-card accent-warning">
                    <div class="metric-label">Subscription Renewals Due</div>
                    <div class="metric-value" id="fin-renewals-due">-</div>
                    <div class="metric-sub">Renewing within 30 days</div>
                </div>
            </div>

            <!-- Visual Charts Breakdown -->
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap:1.5rem; margin-bottom:1.5rem;">
                <div class="card">
                    <div class="card-header"><span class="card-title">📈 Monthly Revenue Trend</span></div>
                    <div style="padding:1.5rem;" id="fin-monthly-trend-chart">Loading trend...</div>
                </div>
                <div class="card">
                    <div class="card-header"><span class="card-title">💰 Cash Received vs Outstanding</span></div>
                    <div style="padding:1.5rem;" id="fin-cash-chart">Loading cash distribution...</div>
                </div>
                <div class="card">
                    <div class="card-header"><span class="card-title">⏳ Overdue Receivables Aging</span></div>
                    <div style="padding:1.5rem;" id="fin-aging-chart">Loading aging buckets...</div>
                </div>
                <div class="card">
                    <div class="card-header"><span class="card-title">📦 Revenue Distribution by Plan</span></div>
                    <div style="padding:1.5rem;" id="fin-plan-chart">Loading plan breakdown...</div>
                </div>
            </div>
        </section>

        <!-- ============================================================= -->
        <!-- TAB 2: MODULE 1 — USER MANAGEMENT & RBAC                       -->
        <!-- ============================================================= -->
        <section id="tab-users" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">👥 User Management & Access Control</span>
                    <div style="display:flex; gap:0.5rem;">
                        <button class="btn btn-primary btn-sm" onclick="openModal('modal-add-user')">+ Add Staff Member</button>
                        <button class="btn btn-outline btn-sm" onclick="openModal('modal-register-cust')">+ Register Customer</button>
                        <button class="btn btn-outline btn-sm" onclick="openModal('modal-reset-pwd')">🔑 Reset Password</button>
                    </div>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Email / Login</th>
                                <th>Role</th>
                                <th>Contact Record</th>
                                <th>Active</th>
                                <th>Permissions</th>
                            </tr>
                        </thead>
                        <tbody id="users-table-body">
                            <!-- Populated dynamically -->
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- ============================================================= -->
        <!-- TAB 3: MODULE 2 — PRODUCTS, VARIANTS, PLANS, DISCOUNTS & TAXES  -->
        <!-- ============================================================= -->
        <section id="tab-products" class="tab-content">
            <!-- Product Variants & Pricing Section -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">📦 Products & Dynamic Variant Pricing</span>
                    <button class="btn btn-primary btn-sm" onclick="openModal('modal-create-product')">+ Create Product</button>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Product / Variant</th>
                                <th>Type</th>
                                <th>Base Price</th>
                                <th>Variant Surcharge</th>
                                <th>Calculated Sales Price</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="products-table-body">
                            <!-- Populated dynamically -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Subscription Plans (Daily, Weekly, Monthly, Yearly) -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🔄 Subscription Billing Plans</span>
                    <button class="btn btn-primary btn-sm" onclick="openModal('modal-create-plan')">+ Create Subscription Plan</button>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Plan Name</th>
                                <th>Billing Cycle</th>
                                <th>Price</th>
                                <th>Min Quantity</th>
                                <th>Pause Policy</th>
                                <th>Early Closure</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="plans-table-body">
                            <!-- Populated dynamically -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Discounts & Taxes Grid -->
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:1.5rem;">
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">🏷️ Discount Rules</span>
                        <button class="btn btn-outline btn-sm" onclick="openModal('modal-create-discount')">+ Create Discount</button>
                    </div>
                    <div class="table-responsive">
                        <table>
                            <thead>
                                <tr><th>Rule Name</th><th>Code</th><th>Type / Value</th><th>Usage</th><th>Status</th></tr>
                            </thead>
                            <tbody id="discounts-table-body"></tbody>
                        </table>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">🏛️ Accounting Tax Rules</span>
                        <button class="btn btn-outline btn-sm" onclick="openModal('modal-create-tax')">+ Add Tax</button>
                    </div>
                    <div class="table-responsive">
                        <table>
                            <thead>
                                <tr><th>Tax Name</th><th>Rate</th><th>Type</th><th>Included in Price</th></tr>
                            </thead>
                            <tbody id="taxes-table-body"></tbody>
                        </table>
                    </div>
                </div>
            </div>
        </section>

        <!-- ============================================================= -->
        <!-- TAB 4: MODULE 3 — QUOTATIONS & SUBSCRIPTIONS                  -->
        <!-- ============================================================= -->
        <section id="tab-subs" class="tab-content">
            <!-- Active Subscriptions with Mandatory Status Lifecycle -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">📑 Subscriptions (Lifecycle: Draft → Quotation → Confirmed → Active → Closed)</span>
                    <button class="btn btn-primary btn-sm" onclick="openModal('modal-create-sub')">+ Create Subscription</button>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Subscription #</th>
                                <th>Customer</th>
                                <th>Plan</th>
                                <th>Recurring Amount</th>
                                <th>Next Billing / Renewal</th>
                                <th>Mandatory Status</th>
                                <th>Lifecycle Actions</th>
                            </tr>
                        </thead>
                        <tbody id="subs-table-body">
                            <!-- Populated dynamically -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Quotations & Quotation Templates -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">📝 Quotations & Quotation Templates</span>
                    <button class="btn btn-outline btn-sm" onclick="openModal('modal-create-quote')">+ Create Quotation</button>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Quotation #</th>
                                <th>Customer</th>
                                <th>Plan</th>
                                <th>Total</th>
                                <th>Status</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody id="quotes-table-body">
                            <!-- Populated dynamically -->
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- ============================================================= -->
        <!-- TAB 5: MODULE 4 — BILLING & PAYMENTS                          -->
        <!-- ============================================================= -->
        <section id="tab-billing" class="tab-content">
            <!-- Automated Billing Trigger Banner -->
            <div class="card" style="padding:1.25rem; background:white; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <h3 style="font-size:1.05rem; font-weight:700;">⚡ Automated Recurring Billing Engine</h3>
                    <p style="font-size:0.85rem; color:var(--gray-600); margin-top:0.25rem;">
                        Identifies active subscriptions reaching their billing date, validates discounts, applies taxes, and prevents duplicate invoices.
                    </p>
                </div>
                <button class="btn btn-primary" onclick="triggerAutomatedBilling()">▶️ Run Automated Billing Now</button>
            </div>

            <!-- Customer Invoices -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🧾 Invoices (Draft → Confirmed → Paid)</span>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Invoice #</th>
                                <th>Customer</th>
                                <th>Date Due</th>
                                <th>Total Amount</th>
                                <th>Residual Balance</th>
                                <th>Invoice State</th>
                                <th>Payment State</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="invoices-table-body">
                            <!-- Populated dynamically -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Payment Records -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">💳 Recorded Payments & Accounting Reconciliations</span>
                    <button class="btn btn-primary btn-sm" onclick="openModal('modal-record-payment')">+ Record Payment</button>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Payment Ref</th>
                                <th>Customer</th>
                                <th>Related Invoice</th>
                                <th>Method</th>
                                <th>Amount</th>
                                <th>Date</th>
                                <th>Txn Ref</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="payments-table-body">
                            <!-- Populated dynamically -->
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- ============================================================= -->
        <!-- TAB 6: INTEGRATED REVENUE GUARDIAN                             -->
        <!-- ============================================================= -->
        <section id="tab-guardian" class="tab-content">
            <div class="card" style="padding:1.25rem; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <h3 style="font-size:1.05rem; font-weight:700;">🛡️ Revenue Guardian Continuous Engine</h3>
                    <p style="font-size:0.85rem; color:var(--gray-600); margin-top:0.25rem;">Detects overdue debt, renewal risks, and expired discount leakage with SHA-256 deduplication.</p>
                </div>
                <button class="btn btn-primary" onclick="triggerGuardianScan()">⚡ Run Guardian Scan</button>
            </div>

            <div class="card">
                <div class="card-header"><span class="card-title">⚠️ Open Anomaly Cases</span></div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr><th>Case #</th><th>Customer</th><th>Rule Code</th><th>Severity</th><th>Amount at Risk</th><th>Recommended Action</th><th>Status</th><th>Resolution</th></tr>
                        </thead>
                        <tbody id="guardian-cases-body"></tbody>
                    </table>
                </div>
            </div>
        </section>
    </main>

    <!-- ============================================================= -->
    <!-- MODALS: USER MANAGEMENT                                       -->
    <!-- ============================================================= -->
    <!-- Modal Add User -->
    <div id="modal-add-user" class="modal">
        <div class="modal-card">
            <div class="modal-header"><h3>Add Staff Member</h3><button onclick="closeModal('modal-add-user')">✕</button></div>
            <div class="modal-body">
                <div class="form-group"><label class="form-label">Full Name</label><input type="text" id="usr-name" class="form-input" placeholder="e.g. John Doe"></div>
                <div class="form-group"><label class="form-label">Email / Login</label><input type="email" id="usr-email" class="form-input" placeholder="john@brightloop.software"></div>
                <div class="form-group"><label class="form-label">Role</label>
                    <select id="usr-role" class="form-select">
                        <option value="staff">Internal Staff</option>
                        <option value="admin">Administrator</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Password (Must be >8 chars, with uppercase, lowercase, special char)</label>
                    <input type="password" id="usr-pwd" class="form-input" placeholder="e.g. StaffSecure@2026">
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="closeModal('modal-add-user')">Cancel</button>
                <button class="btn btn-primary" onclick="submitAddUser()">Create User</button>
            </div>
        </div>
    </div>

    <!-- Modal Register Customer -->
    <div id="modal-register-cust" class="modal">
        <div class="modal-card">
            <div class="modal-header"><h3>Customer Registration</h3><button onclick="closeModal('modal-register-cust')">✕</button></div>
            <div class="modal-body">
                <div class="form-group"><label class="form-label">Company / Customer Name</label><input type="text" id="cust-name" class="form-input" placeholder="e.g. Zenith Tech Ltd"></div>
                <div class="form-group"><label class="form-label">Billing Email</label><input type="email" id="cust-email" class="form-input" placeholder="billing@zenith.io"></div>
                <div class="form-group">
                    <label class="form-label">Password (>8 chars, uppercase, lowercase, special char)</label>
                    <input type="password" id="cust-pwd" class="form-input" placeholder="e.g. ClientP@ss2026">
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="closeModal('modal-register-cust')">Cancel</button>
                <button class="btn btn-primary" onclick="submitRegisterCustomer()">Register Account</button>
            </div>
        </div>
    </div>

    <!-- Modal Reset Password -->
    <div id="modal-reset-pwd" class="modal">
        <div class="modal-card">
            <div class="modal-header"><h3>Reset Account Password</h3><button onclick="closeModal('modal-reset-pwd')">✕</button></div>
            <div class="modal-body">
                <div class="form-group"><label class="form-label">Registered Account Email</label><input type="email" id="rst-email" class="form-input" placeholder="email@domain.com"></div>
                <div class="form-group"><label class="form-label">New Password (>8 chars, uppercase, lowercase, special char)</label><input type="password" id="rst-pwd" class="form-input"></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="closeModal('modal-reset-pwd')">Cancel</button>
                <button class="btn btn-primary" onclick="submitPasswordReset()">Reset Password</button>
            </div>
        </div>
    </div>

    <!-- ============================================================= -->
    <!-- MODALS: PRODUCTS & PLANS                                      -->
    <!-- ============================================================= -->
    <!-- Modal Create Product -->
    <div id="modal-create-product" class="modal">
        <div class="modal-card">
            <div class="modal-header"><h3>Create Product & Variant</h3><button onclick="closeModal('modal-create-product')">✕</button></div>
            <div class="modal-body">
                <div class="form-group"><label class="form-label">Product Name</label><input type="text" id="prd-name" class="form-input" placeholder="e.g. ERP Extension"></div>
                <div class="form-group"><label class="form-label">Base Sales Price (₹)</label><input type="number" id="prd-price" class="form-input" value="1000.0"></div>
                <div class="form-group"><label class="form-label">Cost Price (₹)</label><input type="number" id="prd-cost" class="form-input" value="400.0"></div>
                <div class="form-group"><label class="form-label">Optional Variant Surcharge (e.g. Odoo Brand +₹560)</label><input type="number" id="prd-extra" class="form-input" value="0.0"></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="closeModal('modal-create-product')">Cancel</button>
                <button class="btn btn-primary" onclick="submitCreateProduct()">Save Product</button>
            </div>
        </div>
    </div>

    <!-- Modal Create Plan -->
    <div id="modal-create-plan" class="modal">
        <div class="modal-card">
            <div class="modal-header"><h3>Create Subscription Plan</h3><button onclick="closeModal('modal-create-plan')">✕</button></div>
            <div class="modal-body">
                <div class="form-group"><label class="form-label">Plan Name</label><input type="text" id="pln-name" class="form-input" placeholder="e.g. Startup Pro"></div>
                <div class="form-group"><label class="form-label">Billing Cycle</label>
                    <select id="pln-cycle" class="form-select">
                        <option value="daily">Daily (Custom Extension)</option>
                        <option value="weekly">Weekly</option>
                        <option value="monthly" selected>Monthly</option>
                        <option value="yearly">Yearly</option>
                    </select>
                </div>
                <div class="form-group"><label class="form-label">Price (₹)</label><input type="number" id="pln-price" class="form-input" value="1500.0"></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="closeModal('modal-create-plan')">Cancel</button>
                <button class="btn btn-primary" onclick="submitCreatePlan()">Save Plan</button>
            </div>
        </div>
    </div>

    <!-- Modal Create Discount -->
    <div id="modal-create-discount" class="modal">
        <div class="modal-card">
            <div class="modal-header"><h3>Create Discount Rule</h3><button onclick="closeModal('modal-create-discount')">✕</button></div>
            <div class="modal-body">
                <div class="form-group"><label class="form-label">Discount Name</label><input type="text" id="dsc-name" class="form-input" placeholder="e.g. Festival Offer"></div>
                <div class="form-group"><label class="form-label">Coupon Code</label><input type="text" id="dsc-code" class="form-input" placeholder="e.g. FESTIVAL20"></div>
                <div class="form-group"><label class="form-label">Type</label>
                    <select id="dsc-type" class="form-select">
                        <option value="percentage">Percentage (%)</option>
                        <option value="fixed">Fixed Amount (₹)</option>
                    </select>
                </div>
                <div class="form-group"><label class="form-label">Value</label><input type="number" id="dsc-val" class="form-input" value="10.0"></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="closeModal('modal-create-discount')">Cancel</button>
                <button class="btn btn-primary" onclick="submitCreateDiscount()">Save Discount</button>
            </div>
        </div>
    </div>

    <!-- ============================================================= -->
    <!-- MODAL: RECORD PAYMENT                                         -->
    <!-- ============================================================= -->
    <div id="modal-record-payment" class="modal">
        <div class="modal-card">
            <div class="modal-header"><h3>Record Customer Payment</h3><button onclick="closeModal('modal-record-payment')">✕</button></div>
            <div class="modal-body">
                <div class="form-group"><label class="form-label">Select Unpaid Invoice</label>
                    <select id="pay-inv-id" class="form-select"></select>
                </div>
                <div class="form-group"><label class="form-label">Payment Amount (₹)</label><input type="number" id="pay-amount" class="form-input" placeholder="e.g. 1000.0"></div>
                <div class="form-group"><label class="form-label">Payment Method</label>
                    <select id="pay-method" class="form-select">
                        <option value="bank_transfer">Bank Wire / Transfer</option>
                        <option value="credit_card">Credit / Debit Card</option>
                        <option value="upi">UPI / Instant Transfer</option>
                        <option value="cash">Cash / Cheque</option>
                    </select>
                </div>
                <div class="form-group"><label class="form-label">Transaction Reference</label><input type="text" id="pay-ref" class="form-input" placeholder="e.g. TXN-9988123"></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="closeModal('modal-record-payment')">Cancel</button>
                <button class="btn btn-primary" onclick="submitRecordPayment()">Commit Payment</button>
            </div>
        </div>
    </div>

    <!-- Floating AI Copilot Launcher -->
    <button class="copilot-launcher" onclick="toggleCopilot()" title="Open SubscriptIQ AI Copilot">💬</button>

    <!-- AI Copilot Chat Drawer -->
    <div class="copilot-drawer" id="copilot-drawer">
        <div class="copilot-header">
            <strong>🤖 SubscriptIQ Finance Copilot</strong>
            <button onclick="toggleCopilot()" style="background:none; border:none; color:white; font-size:1.25rem; cursor:pointer;">✕</button>
        </div>
        <div class="copilot-body" id="copilot-chat">
            <div class="chat-bubble chat-bot">
                Hello! I am your <strong>SubscriptIQ Finance Copilot</strong>. I have real-time access to all 5 core subscription modules, metrics, and revenue assurance records. How can I assist you today?
            </div>
        </div>
        <div class="copilot-footer">
            <input type="text" id="copilot-input" class="form-input" placeholder="Ask about MRR, subscriptions, or overdue invoices..." onkeydown="if(event.key==='Enter') sendCopilotQuery()">
            <button class="btn btn-primary btn-sm" onclick="sendCopilotQuery()">Send</button>
        </div>
    </div>

    <!-- Database Explorer Modal -->
    <div id="db-modal" class="modal">
        <div style="background:white; border-radius:12px; width:94%; max-width:1200px; max-height:85vh; display:flex; flex-direction:column; overflow:hidden;">
            <div style="padding:1rem 1.5rem; background:#1e293b; color:white; display:flex; justify-content:space-between; align-items:center;">
                <h3 style="font-size:1.1rem; font-weight:700;">🗄️ SubscriptIQ Live Database Tables</h3>
                <button onclick="toggleDbExplorer()" style="background:none; border:none; color:white; font-size:1.25rem; cursor:pointer;">✕</button>
            </div>
            <div style="padding:0.75rem 1.5rem; background:#f1f5f9; display:flex; gap:0.5rem; overflow-x:auto; border-bottom:1px solid #cbd5e1;" id="db-tabs"></div>
            <div style="flex:1; padding:1.25rem; overflow-y:auto; background:#f8fafc;" id="db-table-content">Loading database tables...</div>
        </div>
    </div>

    <script>
        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 4000);
        }

        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
        }

        function openModal(id) { document.getElementById(id).style.display = 'flex'; }
        function closeModal(id) { document.getElementById(id).style.display = 'none'; }
        function toggleCopilot() {
            const d = document.getElementById('copilot-drawer');
            d.style.display = d.style.display === 'flex' ? 'none' : 'flex';
        }

        async function fetchAllData() {
            try {
                const res = await fetch('/api/master-state');
                const data = await res.json();

                // 1. Module 5 — Business Finance Dashboard
                const m = data.finance_metrics;
                document.getElementById('fin-active-subs').innerText = m.active_subscriptions;
                document.getElementById('fin-recurring-rev').innerText = '₹' + Number(m.total_recurring_revenue).toLocaleString('en-IN', {minimumFractionDigits: 2});
                document.getElementById('fin-mrr').innerText = '₹' + Number(m.mrr).toLocaleString('en-IN', {minimumFractionDigits: 2});
                document.getElementById('fin-arr').innerText = '₹' + Number(m.arr).toLocaleString('en-IN', {minimumFractionDigits: 2});
                document.getElementById('fin-rev-received').innerText = '₹' + Number(m.revenue_received).toLocaleString('en-IN', {minimumFractionDigits: 2});
                document.getElementById('fin-outstanding').innerText = '₹' + Number(m.outstanding_amount).toLocaleString('en-IN', {minimumFractionDigits: 2});
                document.getElementById('fin-overdue').innerText = '₹' + Number(m.overdue_invoice_amount).toLocaleString('en-IN', {minimumFractionDigits: 2});
                document.getElementById('fin-total-inv').innerText = m.total_invoices;
                document.getElementById('fin-total-cust').innerText = m.total_customers;
                document.getElementById('fin-renewals-due').innerText = m.subscription_renewals_due;

                // Visual chart summaries
                document.getElementById('fin-cash-chart').innerHTML = `
                    <div style="display:flex; justify-content:space-between; margin-bottom:0.5rem; font-weight:600;">
                        <span style="color:var(--success)">Received: ₹${Number(m.charts.payments_vs_outstanding.received).toLocaleString('en-IN')}</span>
                        <span style="color:var(--warning)">Outstanding: ₹${Number(m.charts.payments_vs_outstanding.outstanding).toLocaleString('en-IN')}</span>
                    </div>
                    <div style="background:#e2e8f0; height:18px; border-radius:9px; overflow:hidden; display:flex;">
                        <div style="background:var(--success); width:${m.revenue_received / (m.revenue_received + m.outstanding_amount || 1) * 100}%;"></div>
                        <div style="background:var(--warning); width:${m.outstanding_amount / (m.revenue_received + m.outstanding_amount || 1) * 100}%;"></div>
                    </div>
                `;

                document.getElementById('fin-monthly-trend-chart').innerHTML = `
                    <div style="display:flex; align-items:flex-end; gap:0.75rem; height:120px; padding-top:1rem;">
                        ${m.charts.monthly_trend.map(t => `
                            <div style="flex:1; display:flex; flex-direction:column; align-items:center; gap:0.35rem;">
                                <div style="background:var(--primary); width:100%; height:${Math.min(100, (t.revenue / m.mrr) * 80)}px; border-radius:4px 4px 0 0;"></div>
                                <span style="font-size:0.75rem; color:var(--gray-600);">${t.month}</span>
                            </div>
                        `).join('')}
                    </div>
                `;

                document.getElementById('fin-aging-chart').innerHTML = `
                    <ul style="list-style:none; display:flex; flex-direction:column; gap:0.5rem;">
                        <li style="display:flex; justify-content:space-between;"><span>0–14 Days:</span> <strong>₹${Number(m.charts.overdue_aging['0-14_days']).toLocaleString('en-IN')}</strong></li>
                        <li style="display:flex; justify-content:space-between;"><span>15–30 Days:</span> <strong>₹${Number(m.charts.overdue_aging['15-30_days']).toLocaleString('en-IN')}</strong></li>
                        <li style="display:flex; justify-content:space-between;"><span>31–60 Days:</span> <strong>₹${Number(m.charts.overdue_aging['31-60_days']).toLocaleString('en-IN')}</strong></li>
                        <li style="display:flex; justify-content:space-between;"><span>60+ Days:</span> <strong>₹${Number(m.charts.overdue_aging['60+_days']).toLocaleString('en-IN')}</strong></li>
                    </ul>
                `;

                document.getElementById('fin-plan-chart').innerHTML = `
                    <ul style="list-style:none; display:flex; flex-direction:column; gap:0.5rem;">
                        ${Object.keys(m.charts.revenue_by_plan).map(p => `
                            <li style="display:flex; justify-content:space-between;"><span>${p}:</span> <strong>₹${Number(m.charts.revenue_by_plan[p]).toLocaleString('en-IN')}</strong></li>
                        `).join('')}
                    </ul>
                `;

                // 2. Module 1 — Users Table
                const userTbody = document.getElementById('users-table-body');
                userTbody.innerHTML = data.users.map(u => `
                    <tr>
                        <td style="font-weight:600;">${u.name}</td>
                        <td>${u.login}</td>
                        <td><span class="badge ${u.role === 'admin' ? 'badge-critical' : u.role === 'staff' ? 'badge-quotation' : 'badge-active'}">${u.role.toUpperCase()}</span></td>
                        <td>${u.partner_name || 'System Contact'}</td>
                        <td>${u.active ? '<span style="color:var(--success)">✓ Active</span>' : 'Inactive'}</td>
                        <td style="font-size:0.8rem; color:var(--gray-600);">${u.role === 'admin' ? 'Full System Admin' : u.role === 'staff' ? 'Manage Subs & Invoices' : 'Self-Service Portal Only'}</td>
                    </tr>
                `).join('');

                // 3. Module 2 — Products Table
                const prdTbody = document.getElementById('products-table-body');
                prdTbody.innerHTML = data.products.map(p => `
                    <tr>
                        <td style="font-weight:600;">${p.name}</td>
                        <td>${p.type}</td>
                        <td>₹${Number(p.base_price).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                        <td>${p.extra_price > 0 ? `+₹${p.extra_price.toLocaleString('en-IN')}` : '₹0'}</td>
                        <td style="font-weight:700; color:var(--primary);">₹${Number(p.sales_price).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                        <td><span class="badge badge-active">Active</span></td>
                    </tr>
                `).join('');

                // Plans Table
                const plnTbody = document.getElementById('plans-table-body');
                plnTbody.innerHTML = data.plans.map(p => `
                    <tr>
                        <td style="font-weight:600;">${p.name}</td>
                        <td><span class="badge badge-quotation">${p.billing_interval.toUpperCase()}</span></td>
                        <td style="font-weight:700;">₹${Number(p.price).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                        <td>${p.min_quantity || 1}</td>
                        <td>${p.pause_policy || 'Allowed'}</td>
                        <td>${p.early_closure_policy || 'Allowed'}</td>
                        <td><span class="badge badge-active">Active</span></td>
                    </tr>
                `).join('');

                // Discounts Table
                const dscTbody = document.getElementById('discounts-table-body');
                dscTbody.innerHTML = data.discounts.map(d => `
                    <tr>
                        <td style="font-weight:600;">${d.name}</td>
                        <td><code>${d.code}</code></td>
                        <td>${d.discount_type === 'percentage' ? `${d.value}%` : `₹${d.value}`}</td>
                        <td>${d.usage_count} / ${d.max_usage_limit || '∞'}</td>
                        <td><span class="badge badge-active">Valid</span></td>
                    </tr>
                `).join('');

                // Taxes Table
                const taxTbody = document.getElementById('taxes-table-body');
                taxTbody.innerHTML = data.taxes.map(t => `
                    <tr>
                        <td style="font-weight:600;">${t.name}</td>
                        <td>${t.amount}%</td>
                        <td>${t.amount_type}</td>
                        <td>${t.price_include ? 'Yes (Inclusive)' : 'No (Exclusive)'}</td>
                    </tr>
                `).join('');

                // 4. Module 3 — Subscriptions Table
                const subTbody = document.getElementById('subs-table-body');
                subTbody.innerHTML = data.subscriptions.map(s => `
                    <tr>
                        <td style="font-weight:700; font-family:'JetBrains Mono', monospace;">${s.name}</td>
                        <td>${s.partner_name}</td>
                        <td>${s.plan_name}</td>
                        <td style="font-weight:700;">₹${Number(s.recurring_total).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                        <td>${s.next_renewal_date || 'N/A'}</td>
                        <td><span class="badge badge-${s.status}">${s.status.toUpperCase()}</span></td>
                        <td>
                            ${s.status === 'active' ? `
                                <button class="btn btn-outline btn-sm" onclick="subscriptionAction(${s.id}, 'pause')">Pause</button>
                                <button class="btn btn-outline btn-sm" onclick="subscriptionAction(${s.id}, 'close')">Close</button>
                            ` : s.status === 'paused' ? `
                                <button class="btn btn-outline btn-sm" onclick="subscriptionAction(${s.id}, 'resume')">Resume</button>
                            ` : s.status === 'confirmed' ? `
                                <button class="btn btn-success btn-sm" onclick="subscriptionAction(${s.id}, 'activate')">Activate</button>
                            ` : 'Closed'}
                        </td>
                    </tr>
                `).join('');

                // Quotes Table
                const qTbody = document.getElementById('quotes-table-body');
                qTbody.innerHTML = data.quotations.map(q => `
                    <tr>
                        <td style="font-weight:600;">${q.name}</td>
                        <td>${q.partner_name}</td>
                        <td>${q.plan_name}</td>
                        <td>₹${Number(q.total).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                        <td><span class="badge badge-quotation">${q.status.toUpperCase()}</span></td>
                        <td>
                            <button class="btn btn-primary btn-sm" onclick="quotationAction(${q.id}, 'convert')">Convert to Subscription</button>
                        </td>
                    </tr>
                `).join('');

                // 5. Module 4 — Invoices Table
                const invTbody = document.getElementById('invoices-table-body');
                const paySelect = document.getElementById('pay-inv-id');
                paySelect.innerHTML = '<option value="">-- Choose Unpaid Invoice --</option>';

                invTbody.innerHTML = data.invoices.map(i => {
                    if (i.payment_state !== 'paid') {
                        paySelect.innerHTML += `<option value="${i.id}">${i.name} - ${i.partner_name} (Due: ₹${i.amount_residual})</option>`;
                    }
                    return `
                        <tr>
                            <td style="font-weight:700; font-family:'JetBrains Mono', monospace;">${i.name}</td>
                            <td>${i.partner_name}</td>
                            <td>${i.invoice_date_due}</td>
                            <td style="font-weight:700;">₹${Number(i.amount_total).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                            <td style="font-weight:700; color:${i.amount_residual > 0 ? 'var(--danger)' : 'var(--success)'};">₹${Number(i.amount_residual).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                            <td><span class="badge ${i.state === 'posted' ? 'badge-active' : 'badge-draft'}">${i.state.toUpperCase()}</span></td>
                            <td><span class="badge ${i.payment_state === 'paid' ? 'badge-active' : 'badge-critical'}">${i.payment_state.toUpperCase()}</span></td>
                            <td>
                                ${i.payment_state !== 'paid' ? `
                                    <button class="btn btn-outline btn-sm" onclick="promptPaymentForInv(${i.id}, ${i.amount_residual})">Record Payment</button>
                                ` : '<span style="color:var(--success); font-weight:600;">✓ Settled</span>'}
                            </td>
                        </tr>
                    `;
                }).join('');

                // Payments Table
                const payTbody = document.getElementById('payments-table-body');
                payTbody.innerHTML = data.payments.map(p => `
                    <tr>
                        <td style="font-weight:600; font-family:'JetBrains Mono', monospace;">${p.name}</td>
                        <td>${p.partner_name}</td>
                        <td>${p.invoice_name}</td>
                        <td>${p.payment_method}</td>
                        <td style="font-weight:700; color:var(--success);">₹${Number(p.amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                        <td>${p.payment_date}</td>
                        <td><code>${p.transaction_reference}</code></td>
                        <td><span class="badge badge-active">Posted</span></td>
                    </tr>
                `).join('');

                // Guardian Cases
                const gTbody = document.getElementById('guardian-cases-body');
                gTbody.innerHTML = data.guardian_cases.map(c => `
                    <tr>
                        <td style="font-weight:600; font-family:'JetBrains Mono', monospace;">${c.name}</td>
                        <td>${c.partner_name}</td>
                        <td><code>${c.rule_code}</code></td>
                        <td><span class="badge badge-${c.severity}">${c.severity.toUpperCase()}</span></td>
                        <td style="font-weight:700;">₹${Number(c.amount_at_risk).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                        <td style="font-size:0.8rem; color:var(--gray-600);">${c.recommended_action}</td>
                        <td><span class="badge badge-${c.state}">${c.state.toUpperCase()}</span></td>
                        <td>${c.state === 'open' ? `<button class="btn btn-outline btn-sm" onclick="resolveGuardianCase(${c.id})">Resolve</button>` : '✓ Solved'}</td>
                    </tr>
                `).join('');

            } catch (e) {
                console.error("Failed to load state:", e);
            }
        }

        // Action Handlers
        async function submitAddUser() {
            const name = document.getElementById('usr-name').value;
            const login = document.getElementById('usr-email').value;
            const role = document.getElementById('usr-role').value;
            const password = document.getElementById('usr-pwd').value;
            const res = await fetch('/api/users/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, login, role, password})
            });
            const d = await res.json();
            if (d.error) { alert('Validation Error: ' + d.error); return; }
            showToast('✓ Staff Member created successfully!');
            closeModal('modal-add-user');
            fetchAllData();
        }

        async function submitRegisterCustomer() {
            const name = document.getElementById('cust-name').value;
            const login = document.getElementById('cust-email').value;
            const password = document.getElementById('cust-pwd').value;
            const res = await fetch('/api/users/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, login, password})
            });
            const d = await res.json();
            if (d.error) { alert('Validation Error: ' + d.error); return; }
            showToast('✓ Customer account registered!');
            closeModal('modal-register-cust');
            fetchAllData();
        }

        async function submitPasswordReset() {
            const email = document.getElementById('rst-email').value;
            const new_password = document.getElementById('rst-pwd').value;
            const res = await fetch('/api/users/reset', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({email, new_password})
            });
            const d = await res.json();
            if (d.error) { alert('Reset Error: ' + d.error); return; }
            showToast(d.message);
            closeModal('modal-reset-pwd');
        }

        async function submitCreateProduct() {
            const name = document.getElementById('prd-name').value;
            const list_price = parseFloat(document.getElementById('prd-price').value);
            const standard_price = parseFloat(document.getElementById('prd-cost').value);
            const extra_price = parseFloat(document.getElementById('prd-extra').value);
            await fetch('/api/products/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, list_price, standard_price, extra_price})
            });
            showToast('✓ Product & variant created!');
            closeModal('modal-create-product');
            fetchAllData();
        }

        async function submitCreatePlan() {
            const name = document.getElementById('pln-name').value;
            const billing_interval = document.getElementById('pln-cycle').value;
            const price = parseFloat(document.getElementById('pln-price').value);
            await fetch('/api/plans/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, billing_interval, price})
            });
            showToast('✓ Subscription Plan saved!');
            closeModal('modal-create-plan');
            fetchAllData();
        }

        async function submitCreateDiscount() {
            const name = document.getElementById('dsc-name').value;
            const code = document.getElementById('dsc-code').value;
            const discount_type = document.getElementById('dsc-type').value;
            const value = parseFloat(document.getElementById('dsc-val').value);
            await fetch('/api/discounts/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, code, discount_type, value})
            });
            showToast('✓ Discount Rule saved!');
            closeModal('modal-create-discount');
            fetchAllData();
        }

        async function subscriptionAction(subId, act) {
            await fetch('/api/subscriptions/action', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({subscription_id: subId, action: act})
            });
            showToast(`✓ Subscription action '${act}' completed!`);
            fetchAllData();
        }

        async function quotationAction(quoteId, act) {
            await fetch('/api/quotations/action', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({quotation_id: quoteId, action: act})
            });
            showToast(`✓ Quotation converted to active subscription!`);
            fetchAllData();
        }

        async function triggerAutomatedBilling() {
            showToast('⚡ Running Automated Recurring Billing Engine...');
            const res = await fetch('/api/billing/run', {method: 'POST'});
            const data = await res.json();
            showToast(`✓ Billing completed! ${data.invoices_generated} invoices generated.`);
            fetchAllData();
        }

        function promptPaymentForInv(invId, residual) {
            document.getElementById('pay-inv-id').value = invId;
            document.getElementById('pay-amount').value = residual;
            openModal('modal-record-payment');
        }

        async function submitRecordPayment() {
            const invoice_id = parseInt(document.getElementById('pay-inv-id').value);
            const amount = parseFloat(document.getElementById('pay-amount').value);
            const payment_method = document.getElementById('pay-method').value;
            const transaction_reference = document.getElementById('pay-ref').value;
            const res = await fetch('/api/payments/record', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({invoice_id, amount, payment_method, transaction_reference})
            });
            const d = await res.json();
            if (d.error) { alert('Payment Error: ' + d.error); return; }
            showToast('✓ Payment recorded and invoice reconciled!');
            closeModal('modal-record-payment');
            fetchAllData();
        }

        async function triggerGuardianScan() {
            showToast('⚡ Running continuous Revenue Guardian scan...');
            const res = await fetch('/api/scan', {method: 'POST'});
            const d = await res.json();
            showToast(`✓ Scan finished in ${d.duration_ms}ms.`);
            fetchAllData();
        }

        async function resolveGuardianCase(caseId) {
            await fetch('/api/resolve-case', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({case_id: caseId})
            });
            showToast('✓ Risk Case resolved!');
            fetchAllData();
        }

        async function sendCopilotQuery() {
            const input = document.getElementById('copilot-input');
            const q = input.value.trim();
            if (!q) return;
            const chat = document.getElementById('copilot-chat');
            const u = document.createElement('div');
            u.className = 'chat-bubble chat-user';
            u.innerText = q;
            chat.appendChild(u);
            input.value = '';
            chat.scrollTop = chat.scrollHeight;

            const b = document.createElement('div');
            b.className = 'chat-bubble chat-bot';
            b.innerText = 'Analyzing revenue records...';
            chat.appendChild(b);
            chat.scrollTop = chat.scrollHeight;

            try {
                const res = await fetch('/subscriptiq/copilot/ask', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({prompt: q, company_id: 1})
                });
                const d = await res.json();
                b.innerHTML = `<strong>[${d.provider}]</strong><br>${d.response.replace(/\\n/g, '<br>')}`;
            } catch(e) {
                b.innerText = 'Unable to contact copilot right now.';
            }
            chat.scrollTop = chat.scrollHeight;
        }

        // Database Explorer
        let CACHED_DB = null;
        async function toggleDbExplorer() {
            const modal = document.getElementById('db-modal');
            if (modal.style.display === 'flex') { modal.style.display = 'none'; return; }
            modal.style.display = 'flex';
            document.getElementById('db-table-content').innerHTML = '<div style="padding:2rem; text-align:center;">Loading tables...</div>';
            const res = await fetch('/api/db');
            CACHED_DB = await res.json();
            const tabsDiv = document.getElementById('db-tabs');
            tabsDiv.innerHTML = '';
            const tables = Object.keys(CACHED_DB);
            tables.forEach(t => {
                const btn = document.createElement('button');
                btn.className = 'btn btn-outline btn-sm';
                btn.innerText = `${t} (${CACHED_DB[t].length})`;
                btn.onclick = () => renderDbTable(t);
                tabsDiv.appendChild(btn);
            });
            renderDbTable(tables[0]);
        }

        function renderDbTable(tbl) {
            const rows = CACHED_DB[tbl] || [];
            const c = document.getElementById('db-table-content');
            if (!rows.length) { c.innerHTML = `<div style="padding:2rem; text-align:center;">Table <code>${tbl}</code> is empty.</div>`; return; }
            const cols = Object.keys(rows[0]);
            let h = `<h4 style="margin-bottom:0.75rem;">Table: <code>${tbl}</code> (${rows.length} records)</h4><div style="overflow-x:auto; background:white; border-radius:8px; border:1px solid #e2e8f0; max-height:60vh;"><table><thead><tr>`;
            cols.forEach(col => { h += `<th>${col}</th>`; });
            h += '</tr></thead><tbody>';
            rows.forEach(r => {
                h += '<tr>';
                cols.forEach(col => { h += `<td style="font-size:0.8rem; font-family:monospace;">${r[col] !== null ? r[col] : '<span style="color:#cbd5e1">NULL</span>'}</td>`; });
                h += '</tr>';
            });
            h += '</tbody></table></div>';
            c.innerHTML = h;
        }

        // Init
        fetchAllData();
        setInterval(fetchAllData, 6000);
    </script>
</body>
</html>
"""

class MasterServerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
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
            self.wfile.write(HTML_PAGE.encode('utf-8'))

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
            self.send_json({'metrics': metrics, 'cases': cases, 'audit_events': audit_events})

        elif path == '/api/master-state':
            fin_metrics = RevenueCalculator.compute_business_finance_dashboard(GLOBAL_ENV)
            
            # Users
            users = []
            for u in GLOBAL_ENV['res.users'].search([]):
                p_name = u.partner_id.name if hasattr(u.partner_id, 'name') else 'System'
                users.append({'id': u.id, 'name': u.name, 'login': u.login, 'role': u.role, 'partner_name': p_name, 'active': u.active})

            # Products
            products = []
            for p in GLOBAL_ENV['product.product'].search([]):
                tmpl = p.product_tmpl_id
                tmpl_name = tmpl.name if hasattr(tmpl, 'name') else 'Product'
                base_prc = tmpl.list_price if hasattr(tmpl, 'list_price') else 1000.0
                products.append({
                    'id': p.id,
                    'name': p.name or tmpl_name,
                    'type': 'Service / Subscription',
                    'base_price': base_prc,
                    'extra_price': p.price_extra,
                    'sales_price': p.sales_price
                })

            # Plans
            plans = []
            for pl in GLOBAL_ENV['subscriptiq.plan'].search([]):
                plans.append({
                    'id': pl.id,
                    'name': pl.name,
                    'billing_interval': pl.billing_interval,
                    'price': pl.price,
                    'min_quantity': getattr(pl, 'min_quantity', 1),
                    'pause_policy': getattr(pl, 'pause_policy', 'allowed'),
                    'early_closure_policy': getattr(pl, 'early_closure_policy', 'allowed')
                })

            # Discounts
            discounts = []
            for d in GLOBAL_ENV['subscriptiq.discount'].search([]):
                discounts.append({
                    'id': d.id,
                    'name': d.name,
                    'code': d.code,
                    'discount_type': d.discount_type,
                    'value': d.value,
                    'usage_count': d.usage_count,
                    'max_usage_limit': d.max_usage_limit
                })

            # Taxes
            taxes = []
            for t in GLOBAL_ENV['account.tax'].search([]):
                taxes.append({
                    'id': t.id,
                    'name': t.name,
                    'amount': t.amount,
                    'amount_type': t.amount_type,
                    'price_include': t.price_include
                })

            # Subscriptions
            subs = []
            for s in GLOBAL_ENV['sale.order'].search([('subscriptiq_status', '!=', 'quotation')]):
                pl = s.subscriptiq_plan_id or s.plan_id
                pl_name = pl.name if hasattr(pl, 'name') else 'Plan'
                cust = s.partner_id.name if hasattr(s.partner_id, 'name') else 'Customer'
                subs.append({
                    'id': s.id,
                    'name': s.name,
                    'partner_name': cust,
                    'plan_name': pl_name,
                    'recurring_total': getattr(s, 'subscriptiq_recurring_total', getattr(s, 'recurring_total', 1200.0)),
                    'next_renewal_date': getattr(s, 'subscriptiq_next_renewal_date', getattr(s, 'next_renewal_date', '')),
                    'status': getattr(s, 'subscriptiq_status', 'active')
                })

            # Quotations
            quotes = []
            for q in GLOBAL_ENV['sale.order'].search([('subscriptiq_status', '=', 'quotation')]):
                pl = q.subscriptiq_plan_id or q.plan_id
                pl_name = pl.name if hasattr(pl, 'name') else 'Plan'
                cust = q.partner_id.name if hasattr(q.partner_id, 'name') else 'Customer'
                quotes.append({
                    'id': q.id,
                    'name': q.name,
                    'partner_name': cust,
                    'plan_name': pl_name,
                    'total': getattr(q, 'amount_total', 1416.0),
                    'status': 'quotation'
                })

            # Invoices
            invoices = []
            for inv in GLOBAL_ENV['account.move'].search([('move_type', '=', 'out_invoice')]):
                cust = inv.partner_id.name if hasattr(inv.partner_id, 'name') else 'Customer'
                invoices.append({
                    'id': inv.id,
                    'name': inv.name,
                    'partner_name': cust,
                    'invoice_date_due': str(inv.invoice_date_due or ''),
                    'amount_total': float(inv.amount_total),
                    'amount_residual': float(inv.amount_residual),
                    'state': inv.state,
                    'payment_state': inv.payment_state
                })

            # Payments
            payments = []
            for p in GLOBAL_ENV['account.payment'].search([]):
                cust = p.partner_id.name if hasattr(p.partner_id, 'name') else 'Customer'
                inv = p.invoice_id.name if hasattr(p.invoice_id, 'name') else 'Invoice'
                payments.append({
                    'id': p.id,
                    'name': p.name,
                    'partner_name': cust,
                    'invoice_name': inv,
                    'payment_method': p.payment_method,
                    'amount': float(p.amount),
                    'payment_date': str(p.payment_date or ''),
                    'transaction_reference': p.transaction_reference or 'N/A'
                })

            # Guardian Cases
            cases = []
            for c in GLOBAL_ENV['subscriptiq.risk.case'].search([]):
                cust = c.partner_id.name if hasattr(c.partner_id, 'name') else 'Customer'
                rcode = c.rule_id.code if hasattr(c.rule_id, 'code') else 'RULE'
                cases.append({
                    'id': c.id,
                    'name': c.name,
                    'partner_name': cust,
                    'rule_code': rcode,
                    'severity': c.severity,
                    'amount_at_risk': float(c.amount_at_risk),
                    'recommended_action': c.recommended_action,
                    'state': c.state
                })

            self.send_json({
                'finance_metrics': fin_metrics,
                'users': users,
                'products': products,
                'plans': plans,
                'discounts': discounts,
                'taxes': taxes,
                'subscriptions': subs,
                'quotations': quotes,
                'invoices': invoices,
                'payments': payments,
                'guardian_cases': cases
            })

        elif path == '/api/db':
            tables = {}
            for model_name in ['res.users', 'res.partner', 'product.template', 'product.product', 'subscriptiq.plan', 'subscriptiq.discount', 'account.tax', 'sale.order', 'account.move', 'account.payment', 'subscriptiq.risk.case', 'subscriptiq.audit.event']:
                rows = []
                if model_name in GLOBAL_ENV:
                    for rec in GLOBAL_ENV[model_name].search([]):
                        row_dict = {}
                        raw_dict = rec._records[0].__dict__ if rec._records else {}
                        for k, v in raw_dict.items():
                            if k.startswith('_'): continue
                            if hasattr(v, 'name'):
                                row_dict[k] = v.name
                            elif hasattr(v, 'id'):
                                row_dict[k] = v.id
                            elif isinstance(v, (datetime, date)):
                                row_dict[k] = str(v)
                            elif isinstance(v, Decimal):
                                row_dict[k] = float(v)
                            elif isinstance(v, (int, float, str, bool)) or v is None:
                                row_dict[k] = v
                            else:
                                row_dict[k] = str(v)
                        rows.append(row_dict)
                tables[model_name] = rows
            self.send_json(tables)
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

        try:
            if path == '/api/users/add':
                u = ResUsers.create_user(GLOBAL_ENV, params)
                self.send_json({'success': True, 'user_id': u.id})

            elif path == '/api/users/register':
                params['role'] = 'customer'
                u = ResUsers.create_user(GLOBAL_ENV, params)
                self.send_json({'success': True, 'user_id': u.id})

            elif path == '/api/users/reset':
                email = params.get('email', '')
                new_pwd = params.get('new_password', '')
                token = ResUsers.request_password_reset(GLOBAL_ENV, email)
                ResUsers.reset_password_with_token(GLOBAL_ENV, token, new_pwd)
                self.send_json({'success': True, 'message': f'Password for {email} successfully updated.'})

            elif path == '/api/products/create':
                tmpl = GLOBAL_ENV['product.template'].create({
                    'name': params.get('name', 'New Product'),
                    'list_price': float(params.get('list_price', 1000.0)),
                    'standard_price': float(params.get('standard_price', 400.0)),
                    'product_type': 'service'
                })
                extra = float(params.get('extra_price', 0.0))
                GLOBAL_ENV['product.product'].create({
                    'product_tmpl_id': tmpl.id,
                    'price_extra': extra
                })
                self.send_json({'success': True})

            elif path == '/api/plans/create':
                p = GLOBAL_ENV['subscriptiq.plan'].create({
                    'name': params.get('name', 'New Plan'),
                    'billing_interval': params.get('billing_interval', 'monthly'),
                    'price': float(params.get('price', 1000.0))
                })
                self.send_json({'success': True, 'plan_id': p.id})

            elif path == '/api/discounts/create':
                d = GLOBAL_ENV['subscriptiq.discount'].create({
                    'name': params.get('name', 'Promo Discount'),
                    'code': params.get('code', 'PROMO10'),
                    'discount_type': params.get('discount_type', 'percentage'),
                    'value': float(params.get('value', 10.0)),
                    'scope': 'entire_subscription'
                })
                self.send_json({'success': True, 'discount_id': d.id})

            elif path == '/api/subscriptions/action':
                sub_id = params.get('subscription_id')
                act = params.get('action')
                sub = GLOBAL_ENV['sale.order'].browse(sub_id)
                if act == 'pause': sub.action_pause()
                elif act == 'resume': sub.action_resume()
                elif act == 'close': sub.action_close(early=True)
                elif act == 'activate': sub.action_activate_subscription()
                self.send_json({'success': True})

            elif path == '/api/quotations/action':
                qid = params.get('quotation_id')
                q = GLOBAL_ENV['sale.order'].browse(qid)
                q.action_confirm_subscription()
                self.send_json({'success': True})

            elif path == '/api/billing/run':
                res = BillingEngine.execute_automated_billing_run(GLOBAL_ENV)
                self.send_json(res)

            elif path == '/api/payments/record':
                payment = GLOBAL_ENV['account.payment'].record_payment(params)
                self.send_json({'success': True, 'payment_id': payment.id})

            elif path == '/api/scan':
                res = RiskEngine.execute_guardian_scan(GLOBAL_ENV, GLOBAL_ENV.company.id)
                self.send_json(res)

            elif path == '/api/resolve-case':
                case_id = params.get('case_id')
                c = GLOBAL_ENV['subscriptiq.risk.case'].browse(case_id)
                if c:
                    c.write({'state': 'resolved'})
                    self.send_json({'success': True})
                else:
                    self.send_json({'error': 'Case not found'}, status=404)

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

        except (ValidationError, UserError) as e:
            self.send_json({'error': str(e)}, status=400)
        except Exception as e:
            self.send_json({'error': f'Server error: {str(e)}'}, status=500)

def run_server(port=8069):
    server_address = ('', port)
    httpd = HTTPServer(server_address, MasterServerHandler)
    print(f"======================================================================")
    print(f"  SubscriptIQ Full System (Modules 1-5 + Assurance) Running")
    print(f"  Access URL: http://localhost:{port}")
    print(f"======================================================================")
    httpd.serve_forever()

if __name__ == '__main__':
    port = 8069
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    run_server(port)
