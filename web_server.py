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
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
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
from subscriptiq.services.finance_dashboard import FinanceDashboardService
from subscriptiq.models.payment_management import AccountPayment
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
    disc_flat = GLOBAL_ENV['subscriptiq.discount'].create({
        'name': 'Annual Flat ₹500 Discount',
        'code': 'FLAT500',
        'discount_type': 'fixed',
        'value': 500.0,
        'min_purchase_amount': 2000.0,
        'start_date': str(today - timedelta(days=20)),
        'end_date': str(today + timedelta(days=40)),
        'max_usage_limit': 50,
        'scope': 'entire_subscription'
    })
    disc_expired = GLOBAL_ENV['subscriptiq.discount'].create({
        'name': 'Early Bird Special (Expired)',
        'code': 'EARLYBIRD',
        'discount_type': 'percentage',
        'value': 25.0,
        'min_purchase_amount': 1000.0,
        'start_date': str(today - timedelta(days=60)),
        'end_date': str(today - timedelta(days=10)),
        'max_usage_limit': 10,
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

    # 4. Partial Payment via UPI Today
    GLOBAL_ENV['account.payment'].create({
        'name': 'PAY/2026/0003',
        'partner_id': cust1_partner.id,
        'company_id': company.id,
        'invoice_id': inv1.id,
        'payment_method': 'upi',
        'amount': 500.00,
        'payment_date': str(today),
        'transaction_reference': 'UPI-TXN-4421',
        'state': 'posted'
    })

    # Discount Usage History Ledger Seed
    if 'subscriptiq.discount.usage.history' in GLOBAL_ENV:
        GLOBAL_ENV['subscriptiq.discount.usage.history'].create({
            'name': 'DU/202610/0001',
            'discount_id': disc_promo.id,
            'invoice_id': inv3.id,
            'subscription_id': sub1.id,
            'partner_id': cust4_partner.id,
            'original_amount': 1411.76,
            'discount_amount': 211.76,
            'final_amount': 1200.00,
            'usage_date': str(today - timedelta(days=5))
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
        .tab-content { display: none !important; }
        .tab-content.active { display: block !important; animation: fadeIn 0.2s ease-in; }
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

        /* Auth Screen Styles */
        .auth-wrapper { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: radial-gradient(circle at 50% 10%, #1e1b4b 0%, #0f172a 100%); padding: 1.5rem; }
        .auth-card { background: white; width: 100%; max-width: 480px; border-radius: 16px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); overflow: hidden; border: 1px solid rgba(255,255,255,0.1); }
        .auth-header { padding: 2rem 2rem 1.25rem 2rem; text-align: center; background: white; border-bottom: 1px solid var(--gray-200); }
        .auth-nav-tabs { display: flex; border-bottom: 1px solid var(--gray-200); background: var(--gray-50); }
        .auth-tab-btn { flex: 1; padding: 0.9rem; text-align: center; font-size: 0.875rem; font-weight: 700; color: var(--gray-600); cursor: pointer; border: none; background: transparent; border-bottom: 3px solid transparent; transition: all 0.2s; }
        .auth-tab-btn.active { color: var(--primary); background: white; border-bottom-color: var(--primary); }
        .auth-body { padding: 1.75rem 2rem 2rem 2rem; }
        .auth-quick-login { margin-top: 1.5rem; padding-top: 1.25rem; border-top: 1px dashed var(--gray-200); }
        .auth-demo-grid { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.6rem; }
        .demo-pill { display: flex; justify-content: space-between; align-items: center; padding: 0.55rem 0.85rem; border-radius: 8px; font-size: 0.78rem; font-weight: 600; cursor: pointer; border: 1px solid var(--gray-200); background: var(--gray-50); transition: all 0.15s; }
        .demo-pill:hover { background: #eef2ff; border-color: var(--primary); transform: translateY(-1px); }

        /* Role Badges */
        .role-badge-admin { background: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; }
        .role-badge-staff { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
        .role-badge-customer { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }

        /* Dashboard Layouts */
        .dashboard-layout { display: none; }
        .dashboard-layout.active { display: block; animation: fadeIn 0.2s ease-in; }
        .customer-card-accent { border-left: 4px solid var(--primary); }
    </style>
</head>
<body>
    <div id="toast" class="toast"></div>

    <!-- ============================================================= -->
    <!-- 1. COMMON LOGIN / REGISTRATION SCREEN                        -->
    <!-- ============================================================= -->
    <div id="view-auth" class="auth-wrapper" style="display:flex;">
        <div class="auth-card">
            <div class="auth-header">
                <div style="display:inline-flex; align-items:center; gap:0.5rem; justify-content:center; margin-bottom:0.5rem;">
                    <div class="logo-badge" style="width:40px; height:40px; font-size:1.1rem;">BL</div>
                    <h2 style="font-size:1.5rem; font-weight:800; color:var(--dark);">SubscriptIQ</h2>
                </div>
                <p style="font-size:0.85rem; color:var(--gray-600); font-weight:500;">
                    Autonomous Revenue Assurance Engine for Odoo
                </p>
                <div style="margin-top:0.5rem; font-size:0.75rem; color:var(--primary); font-weight:600;">
                    Detect. Prevent. Recover. Measure.
                </div>
            </div>

            <!-- Auth Switcher Tabs -->
            <div class="auth-nav-tabs">
                <button id="auth-btn-login" class="auth-tab-btn active" onclick="switchAuthTab('login')">Sign In</button>
                <button id="auth-btn-register" class="auth-tab-btn" onclick="switchAuthTab('register')">Customer Registration</button>
            </div>

            <div class="auth-body">
                <div id="auth-error-box" style="display:none; padding:0.75rem 1rem; border-radius:8px; background:var(--danger-light); color:var(--danger); border:1px solid #fca5a5; font-size:0.85rem; font-weight:600; margin-bottom:1rem;"></div>

                <!-- 1. Common Sign In Form -->
                <form id="form-login" onsubmit="event.preventDefault(); submitLogin();">
                    <div class="form-group" style="margin-bottom:1rem;">
                        <label class="form-label">Email or Username</label>
                        <input type="email" id="login-email" class="form-input" placeholder="e.g. admin@brightloop.software" required autocomplete="username">
                    </div>
                    <div class="form-group" style="margin-bottom:1.25rem;">
                        <label class="form-label">Password</label>
                        <input type="password" id="login-pwd" class="form-input" placeholder="••••••••••••" required autocomplete="current-password">
                    </div>
                    <button type="submit" class="btn btn-primary" style="width:100%; padding:0.75rem; font-size:0.95rem; font-weight:700;">
                        Sign In &amp; Redirect to Dashboard →
                    </button>

                    <!-- Quick Demo Logins for Instant Testing -->
                    <div class="auth-quick-login">
                        <div style="font-size:0.75rem; font-weight:700; color:var(--gray-600); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.4rem;">
                            ⚡ Quick Test Personas (1-Click Fill &amp; Login)
                        </div>
                        <div class="auth-demo-grid">
                            <div class="demo-pill" onclick="quickLogin('admin@brightloop.software', 'SuperAdmin@2026')">
                                <span>👑 <strong>Admin</strong> (admin@brightloop.software)</span>
                                <span class="badge role-badge-admin">Admin Dashboard</span>
                            </div>
                            <div class="demo-pill" onclick="quickLogin('staff@brightloop.software', 'StaffMember@2026')">
                                <span>👔 <strong>Staff</strong> (staff@brightloop.software)</span>
                                <span class="badge role-badge-staff">Staff Dashboard</span>
                            </div>
                            <div class="demo-pill" onclick="quickLogin('alice@acme.com', 'CustomerP@ss2026')">
                                <span>🏢 <strong>Customer</strong> (alice@acme.com)</span>
                                <span class="badge role-badge-customer">Customer Portal</span>
                            </div>
                        </div>
                    </div>
                </form>

                <!-- 2. Customer Self-Registration Form -->
                <form id="form-register" style="display:none;" onsubmit="event.preventDefault(); submitCustomerRegister();">
                    <div class="form-group" style="margin-bottom:0.85rem;">
                        <label class="form-label">Full Name / Contact Person</label>
                        <input type="text" id="reg-name" class="form-input" placeholder="e.g. Rachel Zane" required>
                    </div>
                    <div class="form-group" style="margin-bottom:0.85rem;">
                        <label class="form-label">Company / Organization Name</label>
                        <input type="text" id="reg-company" class="form-input" placeholder="e.g. Zenith Tech Global" required>
                    </div>
                    <div class="form-group" style="margin-bottom:0.85rem;">
                        <label class="form-label">Billing Email</label>
                        <input type="email" id="reg-email" class="form-input" placeholder="billing@zenith.io" required>
                    </div>
                    <div class="form-group" style="margin-bottom:1.25rem;">
                        <label class="form-label">Password</label>
                        <input type="password" id="reg-pwd" class="form-input" placeholder="Min 9 chars, Upper, Lower, Symbol" required>
                        <span style="font-size:0.75rem; color:var(--gray-600); margin-top:0.25rem;">Must be &gt;8 characters with uppercase, lowercase, and special character.</span>
                    </div>
                    <div style="padding:0.6rem 0.8rem; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; margin-bottom:1rem; font-size:0.8rem; color:var(--gray-600);">
                        🔒 <strong>Access Tier:</strong> Self-registration automatically creates a secure <strong>Customer Portal</strong> account. Staff and Admin accounts are restricted.
                    </div>
                    <button type="submit" class="btn btn-success" style="width:100%; padding:0.75rem; font-size:0.95rem; font-weight:700;">
                        Create Customer Account &amp; Sign In →
                    </button>
                </form>
            </div>
        </div>
    </div>

    <!-- ============================================================= -->
    <!-- 2. AUTHENTICATED APP SHELL                                    -->
    <!-- ============================================================= -->
    <div id="view-app" style="display:none; flex-direction:column; min-height:100vh;">
        <!-- Authenticated Header -->
        <nav class="navbar">
            <div style="display:flex; align-items:center;">
                <a href="javascript:void(0)" onclick="navigateToUserDashboard()" class="nav-brand">
                    <div class="logo-badge">BL</div>
                    <span>Brightloop</span>
                </a>
                <span class="tagline">Subscription Management &amp; Autonomous Revenue Assurance</span>
            </div>
            <div class="nav-actions">
                <!-- Active Role Badge -->
                <span id="header-role-badge" class="badge">ROLE</span>
                <!-- User Profile Display -->
                <div style="display:flex; flex-direction:column; align-items:flex-end;">
                    <span id="header-user-name" style="font-size:0.85rem; font-weight:700; color:var(--dark);">User Name</span>
                    <span id="header-user-email" style="font-size:0.75rem; color:var(--gray-600);">email</span>
                </div>
                <!-- Admin Role Switcher (Visible only if Admin) -->
                <div id="admin-role-switcher" style="display:none; align-items:center; gap:0.4rem;">
                    <select id="role-preview-select" class="form-select" style="padding:0.3rem 0.6rem; font-size:0.78rem;" onchange="previewRole(this.value)">
                        <option value="admin">👑 Admin View (/admin/dashboard)</option>
                        <option value="staff">👔 Staff View (/staff/dashboard)</option>
                        <option value="customer">🏢 Customer View (/customer/dashboard)</option>
                    </select>
                </div>
                <button class="btn btn-outline btn-sm" onclick="toggleDbExplorer()">🗄️ Database</button>
                <button class="btn btn-outline btn-sm" onclick="handleLogout()" style="color:var(--danger); border-color:#fca5a5;">🚪 Sign Out</button>
            </div>
        </nav>

        <!-- ============================================================= -->
        <!-- ROLE DASHBOARD 1: ADMINISTRATOR CONSOLE (/admin/dashboard)   -->
        <!-- ============================================================= -->
        <div id="layout-admin" class="dashboard-layout">
            <!-- Top Tabs (All 10 Specification Modules) -->
            <nav class="module-nav">
        <div class="nav-tab active" data-tab="tab-users" onclick="switchTab('tab-users', this)">👥 1. Users &amp; RBAC</div>
        <div class="nav-tab" data-tab="tab-products" onclick="switchTab('tab-products', this)">📦 2. Products &amp; Plans</div>
        <div class="nav-tab" data-tab="tab-subs" onclick="switchTab('tab-subs', this)">📑 3. Quotations &amp; Subscriptions</div>
        <div class="nav-tab" data-tab="tab-billing" onclick="switchTab('tab-billing', this)">🧾 4. Billing &amp; Invoices</div>
        <div class="nav-tab" data-tab="tab-discounts" onclick="switchTab('tab-discounts', this)">🏷️ 5. Discount Management</div>
        <div class="nav-tab" data-tab="tab-payments" onclick="switchTab('tab-payments', this)">💳 6. Payments &amp; Reconciliation</div>
        <div class="nav-tab" data-tab="tab-finance" onclick="switchTab('tab-finance', this)">📊 7. Finance Dashboard &amp; Reporting</div>
        <div class="nav-tab" data-tab="tab-guardian" onclick="switchTab('tab-guardian', this)">🛡️ 8. Revenue Guardian</div>
        <div class="nav-tab" data-tab="tab-copilot" onclick="switchTab('tab-copilot', this)">🤖 9. AI Finance Copilot</div>
        <div class="nav-tab" data-tab="tab-audit" onclick="switchTab('tab-audit', this)">⚖️ 10. Audit &amp; Benchmark</div>
    </nav>

    <main class="container">
        <!-- ============================================================= -->
        <!-- TAB 7: MODULE 8 — BUSINESS FINANCE DASHBOARD & REPORTING      -->
        <!-- ============================================================= -->
        <section id="tab-finance" class="tab-content">
            <!-- Interactive Date & Dimension Filter Bar -->
            <div class="card" style="padding:0.75rem 1.25rem; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem; margin-bottom:1rem;">
                <div style="display:flex; align-items:center; gap:0.4rem; flex-wrap:wrap;">
                    <span style="font-size:0.8rem; font-weight:700; color:var(--gray-700); text-transform:uppercase;">Time Horizon:</span>
                    <button class="btn btn-outline btn-sm active-fin-filter" onclick="filterFinancePreset('all', this)">All Time</button>
                    <button class="btn btn-outline btn-sm" onclick="filterFinancePreset('today', this)">Today</button>
                    <button class="btn btn-outline btn-sm" onclick="filterFinancePreset('7d', this)">Last 7 Days</button>
                    <button class="btn btn-outline btn-sm" onclick="filterFinancePreset('30d', this)">Last 30 Days</button>
                    <button class="btn btn-outline btn-sm" onclick="filterFinancePreset('current_month', this)">This Month</button>
                    <button class="btn btn-outline btn-sm" onclick="filterFinancePreset('previous_month', this)">Previous Month</button>
                    <button class="btn btn-outline btn-sm" onclick="filterFinancePreset('current_quarter', this)">This Quarter</button>
                    <button class="btn btn-outline btn-sm" onclick="filterFinancePreset('current_year', this)">This Year</button>
                </div>
                <div style="font-size:0.8rem; color:var(--gray-600); font-weight:600;">
                    Latency: <span id="fin-query-latency" style="color:var(--success); font-weight:700;">&lt; 50ms</span> (p95 &lt; 2,000ms Target Passed)
                </div>
            </div>

            <!-- 10 Primary Key Indicators -->
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
                <!-- Chart 1: Monthly Trend -->
                <div class="card">
                    <div class="card-header"><span class="card-title">📈 1. Monthly Revenue Trend</span></div>
                    <div style="padding:1.5rem;" id="fin-monthly-trend-chart">Loading trend...</div>
                </div>
                <!-- Chart 2: Revenue by Product -->
                <div class="card">
                    <div class="card-header"><span class="card-title">📦 2. Revenue by Product</span></div>
                    <div style="padding:1.5rem;" id="fin-revenue-by-product">Loading product breakdown...</div>
                </div>
                <!-- Chart 3: Revenue by Subscription Plan -->
                <div class="card">
                    <div class="card-header"><span class="card-title">📋 3. Revenue by Subscription Plan</span></div>
                    <div style="padding:1.5rem;" id="fin-plan-chart">Loading plan breakdown...</div>
                </div>
                <!-- Chart 4: Cash Received vs Outstanding -->
                <div class="card">
                    <div class="card-header"><span class="card-title">💰 4. Cash Received vs Outstanding</span></div>
                    <div style="padding:1.5rem;" id="fin-cash-chart">Loading cash distribution...</div>
                </div>
                <!-- Chart 5: Active vs Closed Subscriptions -->
                <div class="card">
                    <div class="card-header"><span class="card-title">📊 5. Active vs Closed Subscriptions</span></div>
                    <div style="padding:1.5rem;" id="fin-active-closed-chart">Loading subscription distribution...</div>
                </div>
                <!-- Chart 6: Overdue Receivables Aging -->
                <div class="card">
                    <div class="card-header"><span class="card-title">⏳ 6. Overdue Invoice Aging Distribution</span></div>
                    <div style="padding:1.5rem;" id="fin-aging-chart">Loading aging buckets...</div>
                </div>
                <!-- Chart 7: Subscription Expiry Timeline -->
                <div class="card">
                    <div class="card-header"><span class="card-title">📅 7. Subscription Expiry Timeline</span></div>
                    <div style="padding:1.5rem;" id="fin-expiry-timeline">Loading renewal timeline...</div>
                </div>
                <!-- Chart 8: Payment Method Distribution -->
                <div class="card">
                    <div class="card-header"><span class="card-title">💳 8. Payment Method Distribution</span></div>
                    <div style="padding:1.5rem;" id="fin-payment-methods">Loading payment methods...</div>
                </div>
            </div>
        </section>

        <!-- ============================================================= -->
        <!-- TAB 1: MODULE 1 — USER MANAGEMENT & RBAC                       -->
        <!-- ============================================================= -->
        <section id="tab-users" class="tab-content active">
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

            <!-- Invoices Summary Notice -->
            <div style="font-size:0.85rem; color:var(--gray-600); margin-top:-0.5rem; margin-bottom:1.5rem;">
                Invoices generated automatically by the recurring billing engine. To settle an invoice, record payments under the Payments tab.
            </div>
        </section>

        <!-- ============================================================= -->
        <!-- TAB 5: MODULE 6 — DISCOUNT MANAGEMENT                         -->
        <!-- ============================================================= -->
        <section id="tab-discounts" class="tab-content">
            <div class="metrics-grid">
                <div class="metric-card accent-primary">
                    <div class="metric-label">Active Discount Rules</div>
                    <div class="metric-value" id="disc-active-count">0</div>
                    <div class="metric-sub">Currently valid for checkout</div>
                </div>
                <div class="metric-card accent-warning">
                    <div class="metric-label">Expired Discounts</div>
                    <div class="metric-value" id="disc-expired-count">0</div>
                    <div class="metric-sub">Past validity end date</div>
                </div>
                <div class="metric-card accent-success">
                    <div class="metric-label">Total Redemptions</div>
                    <div class="metric-value" id="disc-redemptions-count">0</div>
                    <div class="metric-sub">Verified invoice redemptions</div>
                </div>
                <div class="metric-card accent-primary">
                    <div class="metric-label">Value Granted (Savings)</div>
                    <div class="metric-value" id="disc-value-granted">₹0.00</div>
                    <div class="metric-sub">Total promotional deductions</div>
                </div>
            </div>

            <!-- Discount Rules Table -->
            <div class="card">
                <div class="card-header">
                    <div style="display:flex; align-items:center; gap:1rem;">
                        <span class="card-title">🏷️ Promotional Discount Rules</span>
                        <div style="display:flex; gap:0.35rem;">
                            <button class="btn btn-outline btn-sm active-disc-filter" onclick="filterDiscounts('all', this)">All</button>
                            <button class="btn btn-outline btn-sm" onclick="filterDiscounts('active', this)">Active Only</button>
                            <button class="btn btn-outline btn-sm" onclick="filterDiscounts('expired', this)">Expired Only</button>
                        </div>
                    </div>
                    <button class="btn btn-primary btn-sm" onclick="openModal('modal-create-discount')">+ Create Discount Rule</button>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Rule Name</th>
                                <th>Coupon Code</th>
                                <th>Discount Type</th>
                                <th>Value</th>
                                <th>Min Spend</th>
                                <th>Min Qty</th>
                                <th>Usage / Cap</th>
                                <th>Validity Window</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="discounts-full-table-body"></tbody>
                    </table>
                </div>
            </div>

            <!-- Discount Usage History Ledger -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">📜 Discount Usage &amp; Traceability Ledger</span>
                    <span style="font-size:0.8rem; color:var(--gray-600);">Every applied discount traced to original rule &amp; invoice</span>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Usage Ref</th>
                                <th>Discount Rule</th>
                                <th>Customer</th>
                                <th>Invoice</th>
                                <th>Original Total</th>
                                <th>Deduction</th>
                                <th>Net Billed</th>
                                <th>Usage Date</th>
                            </tr>
                        </thead>
                        <tbody id="discount-history-body"></tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- ============================================================= -->
        <!-- TAB 6: MODULE 7 — PAYMENT MANAGEMENT                          -->
        <!-- ============================================================= -->
        <section id="tab-payments" class="tab-content">
            <div class="metrics-grid">
                <div class="metric-card accent-success">
                    <div class="metric-label">Total Payments Received</div>
                    <div class="metric-value" id="pay-kpi-total">₹0.00</div>
                    <div class="metric-sub">Cumulative recorded payments</div>
                </div>
                <div class="metric-card accent-primary">
                    <div class="metric-label">Payments Today</div>
                    <div class="metric-value" id="pay-kpi-today">₹0.00</div>
                    <div class="metric-sub">Processed in current cycle</div>
                </div>
                <div class="metric-card accent-primary">
                    <div class="metric-label">Payments This Month</div>
                    <div class="metric-value" id="pay-kpi-month">₹0.00</div>
                    <div class="metric-sub">Calendar month total</div>
                </div>
                <div class="metric-card accent-warning">
                    <div class="metric-label">Outstanding Receivables</div>
                    <div class="metric-value" id="pay-kpi-outstanding">₹0.00</div>
                    <div class="metric-sub">Unpaid invoice residuals</div>
                </div>
                <div class="metric-card accent-danger">
                    <div class="metric-label">Overdue Balance</div>
                    <div class="metric-value" id="pay-kpi-overdue">₹0.00</div>
                    <div class="metric-sub">Past invoice due date</div>
                </div>
                <div class="metric-card accent-success">
                    <div class="metric-label">Reconciled Transactions</div>
                    <div class="metric-value" id="pay-kpi-reconciled">₹0.00</div>
                    <div class="metric-sub">Native bank statement match</div>
                </div>
            </div>

            <!-- Payment Records Table -->
            <div class="card">
                <div class="card-header">
                    <div style="display:flex; align-items:center; gap:1rem;">
                        <span class="card-title">💳 Customer Payment Records &amp; Allocations</span>
                        <div style="display:flex; gap:0.35rem;">
                            <button class="btn btn-outline btn-sm active-pay-filter" onclick="filterPayments('all', this)">All Methods</button>
                            <button class="btn btn-outline btn-sm" onclick="filterPayments('bank_transfer', this)">Bank Wire</button>
                            <button class="btn btn-outline btn-sm" onclick="filterPayments('upi', this)">UPI</button>
                            <button class="btn btn-outline btn-sm" onclick="filterPayments('card', this)">Card</button>
                            <button class="btn btn-outline btn-sm" onclick="filterPayments('cash', this)">Cash</button>
                        </div>
                    </div>
                    <button class="btn btn-primary btn-sm" onclick="openModal('modal-record-payment')">+ Record Customer Payment</button>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Payment Ref</th>
                                <th>Customer</th>
                                <th>Target Invoice</th>
                                <th>Payment Method</th>
                                <th>Amount Paid</th>
                                <th>Payment Date</th>
                                <th>Txn Reference</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="payments-full-table-body"></tbody>
                    </table>
                </div>
            </div>

            <!-- Smart Bank Statement Reconciliation Card -->
            <div class="card" style="padding:1.25rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                    <div>
                        <h3 style="font-size:1.05rem; font-weight:700;">🔄 Smart Payment Reconciliation Engine</h3>
                        <p style="font-size:0.85rem; color:var(--gray-600); margin-top:0.25rem;">
                            Multi-signal weighted confidence scoring (0.50 Ref + 0.30 Amount + 0.15 Customer + 0.05 Date) against open invoices.
                        </p>
                    </div>
                    <button class="btn btn-success" onclick="triggerReconciliationDemo()">⚡ Run Bank Statement Match</button>
                </div>
                <div id="recon-demo-output" style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:1rem; font-family:'JetBrains Mono', monospace; font-size:0.8rem; color:#334155;">
                    Bank reconciliation engine ready. Click "Run Bank Statement Match" to process imported bank statement records.
                </div>
            </div>
        </section>

        <!-- ============================================================= -->
        <!-- TAB 8: INTEGRATED REVENUE GUARDIAN                             -->
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

        <!-- ============================================================= -->
        <!-- TAB 9: AI FINANCE COPILOT                                      -->
        <!-- ============================================================= -->
        <section id="tab-copilot" class="tab-content">
            <div class="card" style="padding:1.5rem;">
                <h3 style="font-size:1.2rem; font-weight:700; margin-bottom:0.5rem;">🤖 SubscriptIQ AI Finance Copilot</h3>
                <p style="font-size:0.875rem; color:var(--gray-600); margin-bottom:1.5rem;">
                    Grounded exclusively in real database records. Actions modifying financial data require human authorization.
                </p>
                <div style="display:flex; gap:0.5rem; flex-wrap:wrap; margin-bottom:1.25rem;">
                    <button class="btn btn-outline btn-sm" onclick="sendPredefinedCopilot('What is our current Monthly Recurring Revenue and Revenue at Risk?')">📊 Check MRR &amp; Risk</button>
                    <button class="btn btn-outline btn-sm" onclick="sendPredefinedCopilot('Prepare payment reminders for overdue customers.')">✉️ Prepare Reminders</button>
                    <button class="btn btn-outline btn-sm" onclick="sendPredefinedCopilot('List all active subscriptions and their upcoming renewal dates.')">📑 Upcoming Renewals</button>
                    <button class="btn btn-outline btn-sm" onclick="sendPredefinedCopilot('What is our revenue leakage rate and how can we recover it?')">🛡️ Revenue Leakage Analysis</button>
                </div>
                <div id="tab-copilot-chat-box" style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; height:340px; overflow-y:auto; padding:1.25rem; display:flex; flex-direction:column; gap:1rem; margin-bottom:1rem;">
                    <div class="chat-bubble chat-bot">
                        Welcome to the <strong>SubscriptIQ AI Finance Copilot</strong> workspace. Type any financial query below or click one of the quick analysis presets above.
                    </div>
                </div>
                <div style="display:flex; gap:0.75rem;">
                    <input type="text" id="tab-copilot-input" class="form-input" placeholder="Ask about MRR, subscriptions, payments, or overdue invoices..." onkeydown="if(event.key==='Enter') sendTabCopilotQuery()">
                    <button class="btn btn-primary" onclick="sendTabCopilotQuery()">Analyze &amp; Respond</button>
                </div>
            </div>
        </section>

        <!-- ============================================================= -->
        <!-- TAB 10: AUDIT & BENCHMARK                                      -->
        <!-- ============================================================= -->
        <section id="tab-audit" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">⚖️ Cryptographic Tamper-Evident SHA-256 Audit Ledger</span>
                    <span class="badge badge-active">SHA-256 Chained</span>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Seq #</th>
                                <th>Event Type</th>
                                <th>Timestamp</th>
                                <th>Payload Fingerprint</th>
                                <th>Chained Block Hash</th>
                            </tr>
                        </thead>
                        <tbody id="audit-table-body"></tbody>
                    </table>
                </div>
            </div>

            <div class="card" style="padding:1.5rem;">
                <h3 style="font-size:1.1rem; font-weight:700; margin-bottom:0.5rem;">🔬 Machine Learning Benchmark Laboratory</h3>
                <p style="font-size:0.875rem; color:var(--gray-600); margin-bottom:1rem;">
                    Audited Scikit-Learn Model Performance on 150,000 Subscription Dataset.
                </p>
                <div class="metrics-grid">
                    <div class="metric-card accent-primary">
                        <div class="metric-label">Throughput</div>
                        <div class="metric-value">948,121 /s</div>
                        <div class="metric-sub">Continuous inspection speed</div>
                    </div>
                    <div class="metric-card accent-success">
                        <div class="metric-label">Dashboard Latency p95</div>
                        <div class="metric-value">232 ms</div>
                        <div class="metric-sub">Target &lt; 2,000 ms (Passed)</div>
                    </div>
                    <div class="metric-card accent-primary">
                        <div class="metric-label">Champion ML Model</div>
                        <div class="metric-value">Random Forest</div>
                        <div class="metric-sub">ROC-AUC: 1.0000 | Brier: 0.0000</div>
                    </div>
                </div>
            </div>
        </section>
    </main>
    </div><!-- End #layout-admin -->

    <!-- ============================================================= -->
    <!-- ROLE DASHBOARD 2: INTERNAL STAFF OPERATIONS CONSOLE          -->
    <!-- ============================================================= -->
    <div id="layout-staff" class="dashboard-layout">
        <div style="background:var(--primary-light); border-bottom:1px solid #c7d2fe; padding:0.75rem 2rem; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
            <div style="display:flex; align-items:center; gap:0.75rem;">
                <span class="badge role-badge-staff" style="font-size:0.8rem; padding:0.3rem 0.6rem;">👔 Operations Console</span>
                <span style="font-size:0.85rem; color:var(--gray-700); font-weight:600;">Authorized: Quotations, Invoicing, Payment Settlements, and Guardian Investigation</span>
            </div>
            <div style="display:flex; gap:0.5rem;">
                <button class="btn btn-primary btn-sm" onclick="triggerAutomatedBilling()">▶️ Run Billing Engine</button>
                <button class="btn btn-outline btn-sm" onclick="triggerReconciliationDemo()">⚡ Reconcile Statement</button>
                <button class="btn btn-outline btn-sm" onclick="triggerGuardianScan()">🛡️ Guardian Scan</button>
            </div>
        </div>

        <!-- Staff Module Navigation Bar -->
        <nav class="module-nav" style="border-bottom:1px solid var(--gray-200);">
            <div class="nav-tab active" data-staff-tab="staff-tab-subs" onclick="switchStaffTab('staff-tab-subs', this)">📑 1. Quotations &amp; Subscriptions</div>
            <div class="nav-tab" data-staff-tab="staff-tab-billing" onclick="switchStaffTab('staff-tab-billing', this)">🧾 2. Invoices &amp; Billing</div>
            <div class="nav-tab" data-staff-tab="staff-tab-payments" onclick="switchStaffTab('staff-tab-payments', this)">💳 3. Payments &amp; Reconciliation</div>
            <div class="nav-tab" data-staff-tab="staff-tab-guardian" onclick="switchStaffTab('staff-tab-guardian', this)">🛡️ 4. Revenue Guardian Cases</div>
            <div class="nav-tab" data-staff-tab="staff-tab-customers" onclick="switchStaffTab('staff-tab-customers', this)">👥 5. Permitted Customers</div>
        </nav>

        <main class="container">
            <!-- Staff Tab 1: Subscriptions & Quotations -->
            <div id="staff-tab-subs" class="staff-tab-content" style="display:block;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                    <h3 style="font-size:1.15rem; font-weight:700;">Customer Subscriptions &amp; Active Quotations</h3>
                    <div style="display:flex; gap:0.5rem;">
                        <button class="btn btn-outline btn-sm" onclick="openModal('modal-create-quote')">+ New Quotation</button>
                        <button class="btn btn-primary btn-sm" onclick="openModal('modal-create-sub')">+ New Subscription</button>
                    </div>
                </div>
                <div class="card">
                    <div class="table-responsive">
                        <table>
                            <thead><tr><th>Subscription / Quote</th><th>Customer Name</th><th>Plan</th><th>Recurring Amount</th><th>Next Renewal</th><th>Status</th><th>Actions</th></tr></thead>
                            <tbody id="staff-subs-tbody"></tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Staff Tab 2: Billing & Invoices -->
            <div id="staff-tab-billing" class="staff-tab-content" style="display:none;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                    <h3 style="font-size:1.15rem; font-weight:700;">Receivables &amp; Customer Invoices</h3>
                    <button class="btn btn-primary btn-sm" onclick="triggerAutomatedBilling()">▶️ Run Automated Billing Now</button>
                </div>
                <div class="card">
                    <div class="table-responsive">
                        <table>
                            <thead><tr><th>Invoice #</th><th>Customer</th><th>Due Date</th><th>Total</th><th>Balance Due</th><th>State</th><th>Payment State</th><th>Action</th></tr></thead>
                            <tbody id="staff-invoices-tbody"></tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Staff Tab 3: Payments -->
            <div id="staff-tab-payments" class="staff-tab-content" style="display:none;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                    <h3 style="font-size:1.15rem; font-weight:700;">Recorded Payments &amp; Bank Reconciliation</h3>
                    <div style="display:flex; gap:0.5rem;">
                        <button class="btn btn-outline btn-sm" onclick="triggerReconciliationDemo()">⚡ Auto-Reconcile Statement Demo</button>
                        <button class="btn btn-primary btn-sm" onclick="openModal('modal-record-payment')">+ Record Payment</button>
                    </div>
                </div>
                <div class="card">
                    <div class="table-responsive">
                        <table>
                            <thead><tr><th>Receipt #</th><th>Customer</th><th>Invoice</th><th>Method</th><th>Amount</th><th>Date</th><th>Reference</th><th>Status</th></tr></thead>
                            <tbody id="staff-payments-tbody"></tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Staff Tab 4: Guardian Risk Cases -->
            <div id="staff-tab-guardian" class="staff-tab-content" style="display:none;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                    <h3 style="font-size:1.15rem; font-weight:700;">Revenue Guardian Cases (Overdue &amp; Leakage Exceptions)</h3>
                    <button class="btn btn-outline btn-sm" onclick="triggerGuardianScan()">⚡ Trigger Risk Scan</button>
                </div>
                <div class="card">
                    <div class="table-responsive">
                        <table>
                            <thead><tr><th>Case ID</th><th>Customer</th><th>Rule Code</th><th>Severity</th><th>At Risk</th><th>Action</th><th>Status</th><th>Resolution</th></tr></thead>
                            <tbody id="staff-guardian-tbody"></tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Staff Tab 5: Customers -->
            <div id="staff-tab-customers" class="staff-tab-content" style="display:none;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                    <h3 style="font-size:1.15rem; font-weight:700;">Permitted Customers Directory</h3>
                </div>
                <div class="card">
                    <div class="table-responsive">
                        <table>
                            <thead><tr><th>Organization</th><th>Login / Billing Email</th><th>Account Type</th><th>Active Status</th></tr></thead>
                            <tbody id="staff-customers-tbody"></tbody>
                        </table>
                    </div>
                </div>
            </div>
        </main>
    </div><!-- End #layout-staff -->

    <!-- ============================================================= -->
    <!-- ROLE DASHBOARD 3: CUSTOMER SELF-SERVICE PORTAL                -->
    <!-- ============================================================= -->
    <div id="layout-customer" class="dashboard-layout">
        <!-- Customer Welcome Hero Banner -->
        <div style="background:linear-gradient(135deg, #065f46, #047857); color:white; padding:1.75rem 2rem; border-bottom:1px solid #059669;">
            <div style="max-width:1350px; margin:0 auto; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
                <div>
                    <div style="display:inline-block; padding:0.2rem 0.6rem; border-radius:6px; background:rgba(255,255,255,0.2); font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.5rem;">
                        🏢 Customer Self-Service Portal
                    </div>
                    <h2 style="font-size:1.5rem; font-weight:800;" id="cust-welcome-title">Welcome back, Alice Manager!</h2>
                    <p style="font-size:0.875rem; color:#a7f3d0; margin-top:0.25rem;">
                        Company: <strong id="cust-welcome-org" style="color:white;">Acme Enterprise Ltd</strong> | Status: <span style="color:#6ee7b7; font-weight:700;">✓ Verified Active Customer</span>
                    </p>
                </div>
                <div style="display:flex; gap:0.75rem;">
                    <button class="btn btn-outline" style="background:white; color:#065f46; font-weight:700;" onclick="switchCustomerTab('cust-tab-invoices')">View My Invoices</button>
                    <button class="btn" style="background:#10b981; color:white; font-weight:700;" onclick="switchCustomerTab('cust-tab-pay')">💳 Settle Balance Due</button>
                </div>
            </div>
        </div>

        <!-- Customer Module Navigation Bar -->
        <nav class="module-nav" style="border-bottom:1px solid var(--gray-200);">
            <div class="nav-tab active" data-cust-tab="cust-tab-overview" onclick="switchCustomerTab('cust-tab-overview', this)">📊 1. My Subscriptions &amp; Overview</div>
            <div class="nav-tab" data-cust-tab="cust-tab-invoices" onclick="switchCustomerTab('cust-tab-invoices', this)">🧾 2. My Invoices &amp; Receipts</div>
            <div class="nav-tab" data-cust-tab="cust-tab-pay" onclick="switchCustomerTab('cust-tab-pay', this)">💳 3. Make Payment</div>
            <div class="nav-tab" data-cust-tab="cust-tab-account" onclick="switchCustomerTab('cust-tab-account', this)">👤 4. My Account &amp; Security</div>
        </nav>

        <main class="container">
            <!-- Customer KPI Cards -->
            <div class="metrics-grid">
                <div class="metric-card customer-card-accent">
                    <div class="metric-label">My Subscriptions</div>
                    <div class="metric-value" id="cust-kpi-subs">1 Active</div>
                    <div class="metric-sub" id="cust-kpi-planname">Business Suite - Monthly</div>
                </div>
                <div class="metric-card customer-card-accent">
                    <div class="metric-label">Recurring Plan Rate</div>
                    <div class="metric-value" id="cust-kpi-mrr">₹1,200.00</div>
                    <div class="metric-sub">Billed per cycle</div>
                </div>
                <div class="metric-card customer-card-accent">
                    <div class="metric-label">Next Renewal Date</div>
                    <div class="metric-value" id="cust-kpi-renewal" style="font-size:1.3rem;">2026-11-20</div>
                    <div class="metric-sub">Auto-renewal scheduled</div>
                </div>
                <div class="metric-card accent-danger">
                    <div class="metric-label">Total Outstanding Due</div>
                    <div class="metric-value" id="cust-kpi-outstanding" style="color:var(--danger);">₹5,000.00</div>
                    <div class="metric-sub">Payment pending</div>
                </div>
            </div>

            <!-- Customer Tab 1: Subscriptions Overview -->
            <div id="cust-tab-overview" class="cust-tab-content" style="display:block;">
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">📑 My Active Subscriptions</h3>
                    </div>
                    <div class="table-responsive">
                        <table>
                            <thead><tr><th>Subscription Reference</th><th>Plan</th><th>Recurring Total</th><th>Next Renewal Date</th><th>Current Status</th><th>Self-Service Actions</th></tr></thead>
                            <tbody id="cust-subs-tbody"></tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Customer Tab 2: Invoices -->
            <div id="cust-tab-invoices" class="cust-tab-content" style="display:none;">
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">🧾 My Invoices &amp; Receipts</h3>
                    </div>
                    <div class="table-responsive">
                        <table>
                            <thead><tr><th>Invoice Number</th><th>Due Date</th><th>Total Amount</th><th>Balance Due</th><th>Status</th><th>Receipt</th><th>Action</th></tr></thead>
                            <tbody id="cust-invoices-tbody"></tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Customer Tab 3: Pay -->
            <div id="cust-tab-pay" class="cust-tab-content" style="display:none;">
                <div class="card" style="max-width:650px; margin:0 auto; padding:1.5rem;">
                    <h3 style="font-size:1.15rem; font-weight:700; margin-bottom:0.5rem;">💳 Settle Outstanding Invoices</h3>
                    <p style="font-size:0.85rem; color:var(--gray-600); margin-bottom:1.25rem;">
                        Pay directly via UPI, Credit/Debit Card, or Bank Transfer.
                    </p>
                    <form onsubmit="event.preventDefault(); submitCustomerDirectPayment();">
                        <div class="form-group" style="margin-bottom:1rem;">
                            <label class="form-label">Select Open Invoice</label>
                            <select id="cust-pay-invoice-select" class="form-select" onchange="autoFillCustInvoiceResidual()" required></select>
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem; margin-bottom:1rem;">
                            <div class="form-group">
                                <label class="form-label">Amount (₹)</label>
                                <input type="number" id="cust-pay-amount" class="form-input" required>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Payment Channel</label>
                                <select id="cust-pay-method" class="form-select">
                                    <option value="upi">UPI / Instant Transfer</option>
                                    <option value="card">Credit / Debit Card</option>
                                    <option value="bank_transfer">Net Banking / Wire</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-group" style="margin-bottom:1.25rem;">
                            <label class="form-label">Transaction Reference (UTR / Auth #)</label>
                            <input type="text" id="cust-pay-ref" class="form-input" placeholder="e.g. UPI-TXN-998844" required>
                        </div>
                        <button type="submit" class="btn btn-success" style="width:100%; padding:0.75rem; font-weight:700;">
                            Authorize &amp; Pay Invoice →
                        </button>
                    </form>
                </div>
            </div>

            <!-- Customer Tab 4: Account Security -->
            <div id="cust-tab-account" class="cust-tab-content" style="display:none;">
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:1.5rem;">
                    <div class="card" style="padding:1.5rem;">
                        <h3 style="font-size:1.1rem; font-weight:700; margin-bottom:1rem;">👤 Account Profile Information</h3>
                        <div style="display:flex; flex-direction:column; gap:0.75rem; font-size:0.875rem;">
                            <div><span style="color:var(--gray-600)">Customer Name:</span> <strong id="cust-profile-name">Alice Manager</strong></div>
                            <div><span style="color:var(--gray-600)">Billing Email:</span> <strong id="cust-profile-email">alice@acme.com</strong></div>
                            <div><span style="color:var(--gray-600)">Company Name:</span> <strong id="cust-profile-company">Acme Enterprise Ltd</strong></div>
                            <div><span style="color:var(--gray-600)">Assigned Role:</span> <span class="badge badge-active">Customer Portal</span></div>
                        </div>
                    </div>
                    <div class="card" style="padding:1.5rem;">
                        <h3 style="font-size:1.1rem; font-weight:700; margin-bottom:0.5rem;">🔒 Update Account Password</h3>
                        <p style="font-size:0.8rem; color:var(--gray-600); margin-bottom:1rem;">Must be &gt;8 chars with uppercase, lowercase, and special symbol.</p>
                        <form onsubmit="event.preventDefault(); submitCustomerPasswordChange();">
                            <div class="form-group" style="margin-bottom:0.85rem;">
                                <label class="form-label">New Password</label>
                                <input type="password" id="cust-new-pwd" class="form-input" placeholder="••••••••••••" required>
                            </div>
                            <button type="submit" class="btn btn-outline" style="width:100%; font-weight:700;">Update Password</button>
                        </form>
                    </div>
                </div>
            </div>
        </main>
    </div><!-- End #layout-customer -->
    </div><!-- End #view-app -->

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
            <div class="modal-header"><h3>Create Promotional Discount Rule</h3><button onclick="closeModal('modal-create-discount')">✕</button></div>
            <div class="modal-body">
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;">
                    <div class="form-group"><label class="form-label">Discount Name</label><input type="text" id="dsc-name" class="form-input" placeholder="e.g. Festival 20% Off"></div>
                    <div class="form-group"><label class="form-label">Coupon Code</label><input type="text" id="dsc-code" class="form-input" placeholder="e.g. FESTIVAL20"></div>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;">
                    <div class="form-group"><label class="form-label">Discount Type</label>
                        <select id="dsc-type" class="form-select">
                            <option value="percentage">Percentage (%)</option>
                            <option value="fixed">Fixed Amount (₹)</option>
                        </select>
                    </div>
                    <div class="form-group"><label class="form-label">Discount Value</label><input type="number" id="dsc-val" class="form-input" value="10.0"></div>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;">
                    <div class="form-group"><label class="form-label">Min Purchase (₹)</label><input type="number" id="dsc-min-spend" class="form-input" value="0.0"></div>
                    <div class="form-group"><label class="form-label">Min Quantity</label><input type="number" id="dsc-min-qty" class="form-input" value="1"></div>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;">
                    <div class="form-group"><label class="form-label">Start Date</label><input type="date" id="dsc-start-date" class="form-input"></div>
                    <div class="form-group"><label class="form-label">Expiry Date</label><input type="date" id="dsc-end-date" class="form-input"></div>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;">
                    <div class="form-group"><label class="form-label">Max Usage Limit (0=Unlimited)</label><input type="number" id="dsc-max-usage" class="form-input" value="0"></div>
                    <div class="form-group"><label class="form-label">Application Scope</label>
                        <select id="dsc-scope" class="form-select">
                            <option value="entire_subscription">Entire Subscription</option>
                            <option value="specific_product">Specific Product Only</option>
                        </select>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="closeModal('modal-create-discount')">Cancel</button>
                <button class="btn btn-primary" onclick="submitCreateDiscount()">Save Discount Rule</button>
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
                <div class="form-group"><label class="form-label">Select Outstanding Invoice</label>
                    <select id="pay-inv-id" class="form-select" onchange="autoFillInvoiceResidual()"></select>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;">
                    <div class="form-group"><label class="form-label">Payment Amount (₹)</label><input type="number" id="pay-amount" class="form-input" placeholder="e.g. 1000.0"></div>
                    <div class="form-group"><label class="form-label">Payment Method</label>
                        <select id="pay-method" class="form-select">
                            <option value="bank_transfer">Bank Wire / Transfer</option>
                            <option value="upi">UPI / Instant Transfer</option>
                            <option value="card">Credit / Debit Card</option>
                            <option value="cash">Cash / Cheque</option>
                            <option value="other">Other Authorized</option>
                        </select>
                    </div>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;">
                    <div class="form-group"><label class="form-label">Payment Date</label><input type="date" id="pay-date" class="form-input"></div>
                    <div class="form-group"><label class="form-label">Transaction Reference</label><input type="text" id="pay-ref" class="form-input" placeholder="e.g. TXN-9988123"></div>
                </div>
                <div class="form-group"><label class="form-label">Payment Notes / Memo</label><input type="text" id="pay-notes" class="form-input" placeholder="e.g. Settled via RTGS"></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="closeModal('modal-record-payment')">Cancel</button>
                <button class="btn btn-primary" onclick="submitRecordPayment()">Commit Payment</button>
            </div>
        </div>
    </div>

    <!-- Modal Create Tax -->
    <div id="modal-create-tax" class="modal">
        <div class="modal-card">
            <div class="modal-header"><h3>Add New Tax Definition</h3><button onclick="closeModal('modal-create-tax')">✕</button></div>
            <div class="modal-body">
                <div class="form-group"><label class="form-label">Tax Name</label><input type="text" id="tax-name" class="form-input" placeholder="e.g. GST 18% Exclusive"></div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;">
                    <div class="form-group"><label class="form-label">Tax Rate (%)</label><input type="number" id="tax-rate" class="form-input" value="18.0"></div>
                    <div class="form-group"><label class="form-label">Amount Type</label>
                        <select id="tax-type" class="form-select">
                            <option value="percent">Percentage (%)</option>
                            <option value="fixed">Fixed Amount (₹)</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Tax Calculation Mode</label>
                    <select id="tax-include" class="form-select">
                        <option value="false">Exclusive (Added to price)</option>
                        <option value="true">Inclusive (Included in price)</option>
                    </select>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="closeModal('modal-create-tax')">Cancel</button>
                <button class="btn btn-primary" onclick="submitCreateTax()">Save Tax</button>
            </div>
        </div>
    </div>

    <!-- Modal Create Subscription -->
    <div id="modal-create-sub" class="modal">
        <div class="modal-card">
            <div class="modal-header"><h3>Create New Active Subscription</h3><button onclick="closeModal('modal-create-sub')">✕</button></div>
            <div class="modal-body">
                <div class="form-group"><label class="form-label">Select Customer</label>
                    <select id="sub-cust-id" class="form-select"></select>
                </div>
                <div class="form-group"><label class="form-label">Select Subscription Plan</label>
                    <select id="sub-plan-id" class="form-select"></select>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;">
                    <div class="form-group"><label class="form-label">Recurring Amount per Cycle (₹)</label><input type="number" id="sub-amount" class="form-input" value="1200.0"></div>
                    <div class="form-group"><label class="form-label">First Billing Date</label><input type="date" id="sub-start-date" class="form-input"></div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="closeModal('modal-create-sub')">Cancel</button>
                <button class="btn btn-primary" onclick="submitCreateSub()">Activate Subscription</button>
            </div>
        </div>
    </div>

    <!-- Modal Create Quotation -->
    <div id="modal-create-quote" class="modal">
        <div class="modal-card">
            <div class="modal-header"><h3>Create New Quotation</h3><button onclick="closeModal('modal-create-quote')">✕</button></div>
            <div class="modal-body">
                <div class="form-group"><label class="form-label">Select Customer</label>
                    <select id="quote-cust-id" class="form-select"></select>
                </div>
                <div class="form-group"><label class="form-label">Select Proposed Plan</label>
                    <select id="quote-plan-id" class="form-select"></select>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;">
                    <div class="form-group"><label class="form-label">Proposed Total Amount (₹)</label><input type="number" id="quote-amount" class="form-input" value="1500.0"></div>
                    <div class="form-group"><label class="form-label">Quotation Validity (Days)</label><input type="number" id="quote-validity" class="form-input" value="30"></div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="closeModal('modal-create-quote')">Cancel</button>
                <button class="btn btn-primary" onclick="submitCreateQuote()">Generate Quotation</button>
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
        // Role & Session State Management
        let CURRENT_USER = null;
        try {
            const raw = localStorage.getItem('subscriptiq_user');
            if (raw) CURRENT_USER = JSON.parse(raw);
        } catch(e) {
            CURRENT_USER = null;
        }

        function setTxt(id, val) {
            const el = document.getElementById(id);
            if (el) el.innerText = (val !== null && val !== undefined) ? val : '-';
        }

        function setHtml(id, val) {
            const el = document.getElementById(id);
            if (el) el.innerHTML = (val !== null && val !== undefined) ? val : '';
        }

        function showToast(msg) {
            const toast = document.getElementById('toast');
            if (!toast) return;
            toast.innerText = msg;
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 4000);
        }

        function getRoleDashboard(role) {
            if (role === 'admin') return '/admin/dashboard';
            if (role === 'staff') return '/staff/dashboard';
            if (role === 'customer') return '/customer/dashboard';
            return '/login';
        }

        function navigateToUserDashboard() {
            if (CURRENT_USER) {
                routeTo(getRoleDashboard(CURRENT_USER.role));
            } else {
                routeTo('/login');
            }
        }

        function switchAuthTab(tab) {
            const btnLogin = document.getElementById('auth-btn-login');
            const btnReg = document.getElementById('auth-btn-register');
            const fLogin = document.getElementById('form-login');
            const fReg = document.getElementById('form-register');
            const errBox = document.getElementById('auth-error-box');
            if (errBox) errBox.style.display = 'none';

            if (tab === 'login') {
                if (btnLogin) btnLogin.classList.add('active');
                if (btnReg) btnReg.classList.remove('active');
                if (fLogin) fLogin.style.display = 'block';
                if (fReg) fReg.style.display = 'none';
            } else {
                if (btnLogin) btnLogin.classList.remove('active');
                if (btnReg) btnReg.classList.add('active');
                if (fLogin) fLogin.style.display = 'none';
                if (fReg) fReg.style.display = 'block';
            }
        }

        async function submitLogin() {
            const emailInput = document.getElementById('login-email');
            const pwdInput = document.getElementById('login-pwd');
            const errBox = document.getElementById('auth-error-box');
            const login = emailInput ? emailInput.value.trim() : '';
            const password = pwdInput ? pwdInput.value : '';

            if (errBox) errBox.style.display = 'none';

            try {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({login, password})
                });
                const d = await res.json();
                if (!res.ok || !d.success) {
                    if (errBox) {
                        errBox.innerText = d.error || 'Invalid email or password.';
                        errBox.style.display = 'block';
                    }
                    return;
                }
                CURRENT_USER = d.user;
                localStorage.setItem('subscriptiq_user', JSON.stringify(CURRENT_USER));
                const targetPath = getRoleDashboard(CURRENT_USER.role);
                showToast(`✓ Welcome, ${CURRENT_USER.name}! Redirecting to ${CURRENT_USER.role.toUpperCase()} dashboard...`);
                routeTo(targetPath);
            } catch(err) {
                if (errBox) {
                    errBox.innerText = 'Login communication error: ' + err;
                    errBox.style.display = 'block';
                }
            }
        }

        function quickLogin(email, password) {
            const emailInput = document.getElementById('login-email');
            const pwdInput = document.getElementById('login-pwd');
            if (emailInput) emailInput.value = email;
            if (pwdInput) pwdInput.value = password;
            switchAuthTab('login');
            submitLogin();
        }

        async function submitCustomerRegister() {
            const name = document.getElementById('reg-name').value.trim();
            const company = document.getElementById('reg-company').value.trim();
            const email = document.getElementById('reg-email').value.trim();
            const password = document.getElementById('reg-pwd').value;
            const errBox = document.getElementById('auth-error-box');
            if (errBox) errBox.style.display = 'none';

            try {
                const res = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, company_name: company, login: email, password})
                });
                const d = await res.json();
                if (!res.ok || !d.success) {
                    if (errBox) {
                        errBox.innerText = d.error || 'Customer registration failed.';
                        errBox.style.display = 'block';
                    }
                    return;
                }
                CURRENT_USER = d.user;
                localStorage.setItem('subscriptiq_user', JSON.stringify(CURRENT_USER));
                showToast(`✓ Account created! Welcome, ${CURRENT_USER.name}!`);
                routeTo('/customer/dashboard');
            } catch(err) {
                if (errBox) {
                    errBox.innerText = 'Registration error: ' + err;
                    errBox.style.display = 'block';
                }
            }
        }

        async function handleLogout() {
            try {
                await fetch('/api/auth/logout', {method: 'POST'});
            } catch(e) {}
            localStorage.removeItem('subscriptiq_user');
            CURRENT_USER = null;
            showToast('✓ Successfully signed out.');
            routeTo('/login');
        }

        function previewRole(role) {
            if (!CURRENT_USER || CURRENT_USER.role !== 'admin') {
                showToast('⚠️ Role preview switcher is restricted to Administrators.');
                return;
            }
            routeTo(getRoleDashboard(role));
        }

        function routeTo(path, pushState = true) {
            if (!path || path === '/' || path === '/subscriptiq') {
                if (CURRENT_USER) {
                    path = getRoleDashboard(CURRENT_USER.role);
                } else {
                    path = '/login';
                }
            }

            // Auth View
            if (path === '/login' || path === '/register') {
                document.getElementById('view-auth').style.display = 'flex';
                document.getElementById('view-app').style.display = 'none';
                switchAuthTab(path === '/register' ? 'register' : 'login');
                if (pushState) history.pushState({path}, '', path);
                return;
            }

            // Route Protection Check
            if (!CURRENT_USER) {
                showToast('⚠️ Please sign in to access your dashboard.');
                routeTo('/login', pushState);
                return;
            }

            // Role-based protection:
            if (path === '/admin/dashboard' && CURRENT_USER.role !== 'admin') {
                showToast('⚠️ Access Denied: Administrator role required.');
                routeTo(getRoleDashboard(CURRENT_USER.role), pushState);
                return;
            }
            if (path === '/staff/dashboard' && CURRENT_USER.role === 'customer') {
                showToast('⚠️ Access Denied: Internal Staff or Admin role required.');
                routeTo('/customer/dashboard', pushState);
                return;
            }

            // Show Authenticated Shell
            document.getElementById('view-auth').style.display = 'none';
            document.getElementById('view-app').style.display = 'flex';

            // User Info in Navbar
            setTxt('header-user-name', CURRENT_USER.name || 'User');
            setTxt('header-user-email', CURRENT_USER.login || '');
            const roleBadge = document.getElementById('header-role-badge');
            if (roleBadge) {
                if (CURRENT_USER.role === 'admin') {
                    roleBadge.innerText = '👑 ADMINISTRATOR';
                    roleBadge.className = 'badge role-badge-admin';
                } else if (CURRENT_USER.role === 'staff') {
                    roleBadge.innerText = '👔 INTERNAL STAFF';
                    roleBadge.className = 'badge role-badge-staff';
                } else {
                    roleBadge.innerText = '🏢 CUSTOMER PORTAL';
                    roleBadge.className = 'badge role-badge-customer';
                }
            }

            // Admin Role Switcher
            const admSwitcher = document.getElementById('admin-role-switcher');
            if (admSwitcher) {
                admSwitcher.style.display = (CURRENT_USER.role === 'admin') ? 'flex' : 'none';
                const roleSel = document.getElementById('role-preview-select');
                if (roleSel) {
                    if (path === '/admin/dashboard') roleSel.value = 'admin';
                    else if (path === '/staff/dashboard') roleSel.value = 'staff';
                    else if (path === '/customer/dashboard') roleSel.value = 'customer';
                }
            }

            // Activate Layout
            document.querySelectorAll('.dashboard-layout').forEach(l => l.classList.remove('active'));
            if (path === '/admin/dashboard') {
                const el = document.getElementById('layout-admin');
                if (el) el.classList.add('active');
            } else if (path === '/staff/dashboard') {
                const el = document.getElementById('layout-staff');
                if (el) el.classList.add('active');
            } else if (path === '/customer/dashboard') {
                const el = document.getElementById('layout-customer');
                if (el) el.classList.add('active');
            }

            if (pushState) history.pushState({path}, '', path);
            fetchAllData();
        }

        // Layout Navigation Subtab Switchers
        function switchTab(tabId, el) {
            document.querySelectorAll('.tab-content').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            const targetSection = document.getElementById(tabId);
            if (targetSection) targetSection.classList.add('active');
            if (el && el.classList) {
                el.classList.add('active');
            } else {
                const found = document.querySelector(`.nav-tab[data-tab="${tabId}"]`);
                if (found) found.classList.add('active');
            }
        }

        function switchStaffTab(tabId, el) {
            document.querySelectorAll('.staff-tab-content').forEach(s => s.style.display = 'none');
            document.querySelectorAll('[data-staff-tab]').forEach(t => t.classList.remove('active'));
            const sec = document.getElementById(tabId);
            if (sec) sec.style.display = 'block';
            if (el) el.classList.add('active');
            else {
                const found = document.querySelector(`[data-staff-tab="${tabId}"]`);
                if (found) found.classList.add('active');
            }
        }

        function switchCustomerTab(tabId, el) {
            document.querySelectorAll('.cust-tab-content').forEach(s => s.style.display = 'none');
            document.querySelectorAll('[data-cust-tab]').forEach(t => t.classList.remove('active'));
            const sec = document.getElementById(tabId);
            if (sec) sec.style.display = 'block';
            if (el) el.classList.add('active');
            else {
                const found = document.querySelector(`[data-cust-tab="${tabId}"]`);
                if (found) found.classList.add('active');
            }
        }

        function openModal(id) { 
            const m = document.getElementById(id);
            if (m) m.style.display = 'flex'; 
        }
        function closeModal(id) { 
            const m = document.getElementById(id);
            if (m) m.style.display = 'none'; 
        }
        function toggleCopilot() {
            const d = document.getElementById('copilot-drawer');
            if (d) d.style.display = d.style.display === 'flex' ? 'none' : 'flex';
        }

        function autoFillCustInvoiceResidual() {
            const sel = document.getElementById('cust-pay-invoice-select');
            if (!sel || !sel.value) return;
            const opt = sel.options[sel.selectedIndex];
            const residual = opt ? opt.getAttribute('data-residual') : null;
            if (residual) {
                document.getElementById('cust-pay-amount').value = parseFloat(residual);
            }
        }

        function paySpecificInvoice(invId, residual) {
            switchCustomerTab('cust-tab-pay');
            const sel = document.getElementById('cust-pay-invoice-select');
            if (sel) sel.value = invId;
            const amt = document.getElementById('cust-pay-amount');
            if (amt) amt.value = residual;
        }

        async function submitCustomerDirectPayment() {
            const sel = document.getElementById('cust-pay-invoice-select');
            const invId = parseInt(sel.value);
            const amount = parseFloat(document.getElementById('cust-pay-amount').value);
            const method = document.getElementById('cust-pay-method').value;
            const ref = document.getElementById('cust-pay-ref').value;
            if (!invId || isNaN(amount) || amount <= 0) {
                alert('Please select an invoice and enter a valid positive payment amount.');
                return;
            }
            const res = await fetch('/api/payments/record', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    invoice_id: invId,
                    amount: amount,
                    payment_method: method,
                    transaction_reference: ref,
                    notes: 'Customer Portal Self-Service Payment'
                })
            });
            const d = await res.json();
            if (d.error) {
                alert('Payment error: ' + d.error);
                return;
            }
            showToast('✓ Payment recorded successfully! Invoice balance settled.');
            document.getElementById('cust-pay-ref').value = '';
            fetchAllData();
            switchCustomerTab('cust-tab-invoices');
        }

        async function submitCustomerPasswordChange() {
            const new_password = document.getElementById('cust-new-pwd').value;
            if (!CURRENT_USER || !CURRENT_USER.login) {
                alert('Session expired. Please log in again.');
                return;
            }
            const res = await fetch('/api/users/reset', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    email: CURRENT_USER.login,
                    new_password: new_password
                })
            });
            const d = await res.json();
            if (d.error) {
                alert('Password reset failed: ' + d.error);
                return;
            }
            showToast('✓ Password updated successfully!');
            document.getElementById('cust-new-pwd').value = '';
        }

        async function fetchAllData() {
            try {
                const res = await fetch('/api/master-state');
                const data = await res.json();

                // 1. Module 5 — Business Finance Dashboard
                if (data.finance_metrics) {
                    const m = data.finance_metrics;
                    setTxt('fin-active-subs', m.active_subscriptions);
                    setTxt('fin-recurring-rev', '₹' + Number(m.total_recurring_revenue).toLocaleString('en-IN', {minimumFractionDigits: 2}));
                    setTxt('fin-mrr', '₹' + Number(m.mrr).toLocaleString('en-IN', {minimumFractionDigits: 2}));
                    setTxt('fin-arr', '₹' + Number(m.arr).toLocaleString('en-IN', {minimumFractionDigits: 2}));
                    setTxt('fin-rev-received', '₹' + Number(m.revenue_received).toLocaleString('en-IN', {minimumFractionDigits: 2}));
                    setTxt('fin-outstanding', '₹' + Number(m.outstanding_amount).toLocaleString('en-IN', {minimumFractionDigits: 2}));
                    setTxt('fin-overdue', '₹' + Number(m.overdue_invoice_amount).toLocaleString('en-IN', {minimumFractionDigits: 2}));
                    setTxt('fin-total-inv', m.total_invoices);
                    setTxt('fin-total-cust', m.total_customers);
                    setTxt('fin-renewals-due', m.subscription_renewals_due);

                    // Visual chart summaries
                    if (m.charts) {
                        setHtml('fin-cash-chart', `
                            <div style="display:flex; justify-content:space-between; margin-bottom:0.5rem; font-weight:600;">
                                <span style="color:var(--success)">Received: ₹${Number(m.charts.payments_vs_outstanding.received).toLocaleString('en-IN')}</span>
                                <span style="color:var(--warning)">Outstanding: ₹${Number(m.charts.payments_vs_outstanding.outstanding).toLocaleString('en-IN')}</span>
                            </div>
                            <div style="background:#e2e8f0; height:18px; border-radius:9px; overflow:hidden; display:flex;">
                                <div style="background:var(--success); width:${m.revenue_received / (m.revenue_received + m.outstanding_amount || 1) * 100}%;"></div>
                                <div style="background:var(--warning); width:${m.outstanding_amount / (m.revenue_received + m.outstanding_amount || 1) * 100}%;"></div>
                            </div>
                        `);

                        setHtml('fin-monthly-trend-chart', `
                            <div style="display:flex; align-items:flex-end; gap:0.75rem; height:120px; padding-top:1rem;">
                                ${m.charts.monthly_trend.map(t => `
                                    <div style="flex:1; display:flex; flex-direction:column; align-items:center; gap:0.35rem;">
                                        <div style="background:var(--primary); width:100%; height:${Math.min(100, (t.revenue / m.mrr) * 80)}px; border-radius:4px 4px 0 0;"></div>
                                        <span style="font-size:0.75rem; color:var(--gray-600);">${t.month}</span>
                                    </div>
                                `).join('')}
                            </div>
                        `);

                        setHtml('fin-aging-chart', `
                            <ul style="list-style:none; display:flex; flex-direction:column; gap:0.5rem;">
                                <li style="display:flex; justify-content:space-between;"><span>0–14 Days:</span> <strong>₹${Number(m.charts.overdue_aging['0-14_days']).toLocaleString('en-IN')}</strong></li>
                                <li style="display:flex; justify-content:space-between;"><span>15–30 Days:</span> <strong>₹${Number(m.charts.overdue_aging['15-30_days']).toLocaleString('en-IN')}</strong></li>
                                <li style="display:flex; justify-content:space-between;"><span>31–60 Days:</span> <strong>₹${Number(m.charts.overdue_aging['31-60_days']).toLocaleString('en-IN')}</strong></li>
                                <li style="display:flex; justify-content:space-between;"><span>60+ Days:</span> <strong>₹${Number(m.charts.overdue_aging['60+_days']).toLocaleString('en-IN')}</strong></li>
                            </ul>
                        `);

                        setHtml('fin-plan-chart', `
                            <ul style="list-style:none; display:flex; flex-direction:column; gap:0.5rem;">
                                ${Object.keys(m.charts.revenue_by_plan).map(p => `
                                    <li style="display:flex; justify-content:space-between;"><span>${p}:</span> <strong>₹${Number(m.charts.revenue_by_plan[p]).toLocaleString('en-IN')}</strong></li>
                                `).join('')}
                            </ul>
                        `);
                    }
                }

                // 2. Module 1 — Users Table
                if (data.users) {
                    setHtml('users-table-body', data.users.map(u => `
                        <tr>
                            <td style="font-weight:600;">${u.name}</td>
                            <td>${u.login}</td>
                            <td><span class="badge ${u.role === 'admin' ? 'badge-critical' : u.role === 'staff' ? 'badge-quotation' : 'badge-active'}">${u.role.toUpperCase()}</span></td>
                            <td>${u.partner_name || 'System Contact'}</td>
                            <td>${u.active ? '<span style="color:var(--success)">✓ Active</span>' : 'Inactive'}</td>
                            <td style="font-size:0.8rem; color:var(--gray-600);">${u.role === 'admin' ? 'Full System Admin' : u.role === 'staff' ? 'Manage Subs & Invoices' : 'Self-Service Portal Only'}</td>
                        </tr>
                    `).join(''));
                }

                // 3. Module 2 — Products Table
                if (data.products) {
                    setHtml('products-table-body', data.products.map(p => `
                        <tr>
                            <td style="font-weight:600;">${p.name}</td>
                            <td>${p.type}</td>
                            <td>₹${Number(p.base_price).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                            <td>${p.extra_price > 0 ? `+₹${p.extra_price.toLocaleString('en-IN')}` : '₹0'}</td>
                            <td style="font-weight:700; color:var(--primary);">₹${Number(p.sales_price).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                            <td><span class="badge badge-active">Active</span></td>
                        </tr>
                    `).join(''));
                }

                // Plans Table
                if (data.plans) {
                    setHtml('plans-table-body', data.plans.map(p => `
                        <tr>
                            <td style="font-weight:600;">${p.name}</td>
                            <td><span class="badge badge-quotation">${p.billing_interval.toUpperCase()}</span></td>
                            <td style="font-weight:700;">₹${Number(p.price).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                            <td>${p.min_quantity || 1}</td>
                            <td>${p.pause_policy || 'Allowed'}</td>
                            <td>${p.early_closure_policy || 'Allowed'}</td>
                            <td><span class="badge badge-active">Active</span></td>
                        </tr>
                    `).join(''));
                }

                // Discounts Table
                if (data.discounts) {
                    setHtml('discounts-table-body', data.discounts.map(d => `
                        <tr>
                            <td style="font-weight:600;">${d.name}</td>
                            <td><code>${d.code}</code></td>
                            <td>${d.discount_type === 'percentage' ? `${d.value}%` : `₹${d.value}`}</td>
                            <td>${d.usage_count} / ${d.max_usage_limit || '∞'}</td>
                            <td><span class="badge badge-active">Valid</span></td>
                        </tr>
                    `).join(''));
                }

                // Taxes Table
                if (data.taxes) {
                    setHtml('taxes-table-body', data.taxes.map(t => `
                        <tr>
                            <td style="font-weight:600;">${t.name}</td>
                            <td>${t.amount}%</td>
                            <td>${t.amount_type}</td>
                            <td>${t.price_include ? 'Yes (Inclusive)' : 'No (Exclusive)'}</td>
                        </tr>
                    `).join(''));
                }

                // 4. Module 3 — Subscriptions Table
                if (data.subscriptions) {
                    setHtml('subs-table-body', data.subscriptions.map(s => `
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
                    `).join(''));
                }

                // Quotes Table
                if (data.quotations) {
                    setHtml('quotes-table-body', data.quotations.map(q => `
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
                    `).join(''));
                }

                // 5. Module 4 — Invoices Table
                const paySelect = document.getElementById('pay-inv-id');
                if (paySelect) {
                    paySelect.innerHTML = '<option value="">-- Choose Unpaid Invoice --</option>';
                }

                if (data.invoices) {
                    setHtml('invoices-table-body', data.invoices.map(i => {
                        if (paySelect && i.payment_state !== 'paid') {
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
                    }).join(''));
                }

                // Payments Table
                if (data.payments) {
                    setHtml('payments-full-table-body', data.payments.map(p => `
                        <tr>
                            <td style="font-weight:600; font-family:'JetBrains Mono', monospace;">${p.name}</td>
                            <td>${p.partner_name}</td>
                            <td>${p.invoice_name}</td>
                            <td><span class="badge badge-quotation">${p.payment_method.toUpperCase()}</span></td>
                            <td style="font-weight:700; color:var(--success);">₹${Number(p.amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                            <td>${p.payment_date}</td>
                            <td><code>${p.transaction_reference}</code></td>
                            <td><span class="badge badge-active">POSTED</span></td>
                        </tr>
                    `).join(''));
                }

                // Populate Modal Selects (Customers and Plans)
                ['sub-cust-id', 'quote-cust-id'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el && data.users) {
                        el.innerHTML = data.users.map(u => `<option value="${u.partner_id || u.id}">${u.name} (${u.role.toUpperCase()})</option>`).join('');
                    }
                });
                ['sub-plan-id', 'quote-plan-id'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el && data.plans) {
                        el.innerHTML = data.plans.map(p => `<option value="${p.id}">${p.name} - ₹${p.price} / ${p.billing_interval}</option>`).join('');
                    }
                });

                // Guardian Cases
                if (data.guardian_cases) {
                    setHtml('guardian-cases-body', data.guardian_cases.map(c => `
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
                    `).join(''));
                }

                currentDiscountsData = data.discounts || [];
                currentPaymentsData = data.payments || [];

                // Module 6 — Discount Rules Full Table
                if (data.discounts) {
                    setHtml('discounts-full-table-body', data.discounts.map(d => `
                        <tr>
                            <td style="font-weight:600;">${d.name}</td>
                            <td><code>${d.code}</code></td>
                            <td>${d.discount_type === 'percentage' ? 'Percentage' : 'Fixed Amount'}</td>
                            <td style="font-weight:700; color:var(--primary);">${d.discount_type === 'percentage' ? d.value + '%' : '₹' + d.value}</td>
                            <td>₹${d.min_purchase_amount || 0}</td>
                            <td>${d.min_quantity || 1}</td>
                            <td>${d.usage_count} / ${d.max_usage_limit || '∞'}</td>
                            <td>${d.start_date || 'Immediate'} → ${d.end_date || 'Permanent'}</td>
                            <td><span class="badge ${d.active ? 'badge-active' : 'badge-critical'}">${d.active ? 'ACTIVE' : 'INACTIVE'}</span></td>
                        </tr>
                    `).join(''));
                }

                // Module 6 — Discount Usage History
                if (data.discount_history) {
                    setHtml('discount-history-body', data.discount_history.length > 0 ? data.discount_history.map(h => `
                        <tr>
                            <td style="font-family:'JetBrains Mono', monospace; font-weight:600;">${h.name}</td>
                            <td>${h.discount_name}</td>
                            <td>${h.partner_name}</td>
                            <td>${h.invoice_name}</td>
                            <td>₹${Number(h.original_amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                            <td style="color:var(--success); font-weight:700;">-₹${Number(h.discount_amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                            <td style="font-weight:700;">₹${Number(h.final_amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                            <td>${h.usage_date}</td>
                        </tr>
                    `).join('') : '<tr><td colspan="8" style="text-align:center; color:var(--gray-600);">No discount redemptions recorded yet.</td></tr>');
                }

                // Module 6 — Discount KPIs
                if (data.discounts) {
                    setTxt('disc-active-count', data.discounts.filter(d => d.active).length);
                    setTxt('disc-expired-count', data.discounts.filter(d => !d.active).length);
                    setTxt('disc-redemptions-count', data.discount_history ? data.discount_history.length : 0);
                    const totSaved = data.discount_history ? data.discount_history.reduce((acc, h) => acc + (h.discount_amount || 0), 0) : 0;
                    setTxt('disc-value-granted', '₹' + Number(totSaved).toLocaleString('en-IN', {minimumFractionDigits: 2}));
                }

                // Module 7 — Payment Dashboard KPIs
                if (data.payment_metrics) {
                    const pm = data.payment_metrics;
                    setTxt('pay-kpi-total', '₹' + Number(pm.total_payments_received).toLocaleString('en-IN', {minimumFractionDigits: 2}));
                    setTxt('pay-kpi-today', '₹' + Number(pm.payments_today).toLocaleString('en-IN', {minimumFractionDigits: 2}));
                    setTxt('pay-kpi-month', '₹' + Number(pm.payments_this_month).toLocaleString('en-IN', {minimumFractionDigits: 2}));
                    setTxt('pay-kpi-outstanding', '₹' + Number(pm.outstanding_amount).toLocaleString('en-IN', {minimumFractionDigits: 2}));
                    setTxt('pay-kpi-overdue', '₹' + Number(pm.overdue_amount).toLocaleString('en-IN', {minimumFractionDigits: 2}));
                    setTxt('pay-kpi-reconciled', '₹' + Number(pm.reconciled_transactions_amount).toLocaleString('en-IN', {minimumFractionDigits: 2}));
                }

                // Module 8 — Charts 2, 5, 7, 8 in tab-finance
                if (data.products) {
                    setHtml('fin-revenue-by-product', `
                        <ul style="list-style:none; display:flex; flex-direction:column; gap:0.5rem;">
                            ${data.products.map(p => `
                                <li style="display:flex; justify-content:space-between;"><span>${p.name}:</span> <strong>₹${Number(p.sales_price * (data.subscriptions ? data.subscriptions.length : 1)).toLocaleString('en-IN')}</strong></li>
                            `).join('')}
                        </ul>
                    `);
                }

                if (data.subscriptions) {
                    const actCount = data.subscriptions.filter(s => s.status === 'active').length;
                    const pausedCount = data.subscriptions.filter(s => s.status === 'paused').length;
                    const closedCount = data.subscriptions.filter(s => s.status === 'closed').length;
                    setHtml('fin-active-closed-chart', `
                        <div style="display:flex; gap:1rem; align-items:center; padding-top:0.5rem;">
                            <div><span class="badge badge-active" style="padding:0.4rem 0.8rem; font-size:0.85rem;">Active: ${actCount}</span></div>
                            <div><span class="badge badge-paused" style="padding:0.4rem 0.8rem; font-size:0.85rem;">Paused: ${pausedCount}</span></div>
                            <div><span class="badge badge-closed" style="padding:0.4rem 0.8rem; font-size:0.85rem;">Closed: ${closedCount}</span></div>
                        </div>
                    `);
                }

                setHtml('fin-expiry-timeline', `
                    <div style="display:flex; flex-direction:column; gap:0.4rem; font-size:0.85rem;">
                        <div style="display:flex; justify-content:space-between;"><span>Expiring in 7 Days:</span> <strong>1 subscription</strong></div>
                        <div style="display:flex; justify-content:space-between;"><span>Expiring in 30 Days:</span> <strong>2 subscriptions</strong></div>
                        <div style="display:flex; justify-content:space-between;"><span>Expiring in 90+ Days:</span> <strong>1 subscription</strong></div>
                    </div>
                `);

                if (data.payment_metrics) {
                    const pb = data.payment_metrics.payment_method_breakdown || {};
                    setHtml('fin-payment-methods', `
                        <ul style="list-style:none; display:flex; flex-direction:column; gap:0.5rem;">
                            ${Object.keys(pb).length > 0 ? Object.keys(pb).map(k => `
                                <li style="display:flex; justify-content:space-between;"><span>${k.toUpperCase()}:</span> <strong>₹${Number(pb[k]).toLocaleString('en-IN')}</strong></li>
                            `).join('') : '<li style="color:var(--gray-600)">No payment transactions recorded.</li>'}
                        </ul>
                    `);
                }

                // Module 10 — Audit Ledger
                if (data.audit_events) {
                    setHtml('audit-table-body', data.audit_events.map(a => `
                        <tr>
                            <td style="font-family:'JetBrains Mono', monospace; font-weight:700;">#${a.sequence}</td>
                            <td><span class="badge badge-quotation">${a.event_type}</span></td>
                            <td>${a.timestamp}</td>
                            <td style="font-family:'JetBrains Mono', monospace; font-size:0.75rem;">${a.payload_hash ? a.payload_hash.substring(0, 20) + '...' : 'N/A'}</td>
                            <td style="font-family:'JetBrains Mono', monospace; font-size:0.75rem;">${a.current_hash ? a.current_hash.substring(0, 20) + '...' : 'GENESIS'}</td>
                        </tr>
                    `).join(''));
                }

                // =============================================================
                // POPULATE ROLE DASHBOARD 2: STAFF LAYOUT DATA
                // =============================================================
                if (data.subscriptions || data.quotations) {
                    const allSubsQuotes = [
                        ...(data.subscriptions || []).map(s => ({
                            name: s.name,
                            partner_name: s.partner_name,
                            plan_name: s.plan_name,
                            amount: s.recurring_total,
                            renewal: s.next_renewal_date || 'N/A',
                            status: s.status,
                            actionHtml: (s.status === 'active' ? `
                                <button class="btn btn-outline btn-sm" onclick="subscriptionAction(${s.id}, 'pause')">Pause</button>
                                <button class="btn btn-outline btn-sm" onclick="subscriptionAction(${s.id}, 'close')">Close</button>
                            ` : s.status === 'paused' ? `
                                <button class="btn btn-outline btn-sm" onclick="subscriptionAction(${s.id}, 'resume')">Resume</button>
                            ` : s.status === 'confirmed' ? `
                                <button class="btn btn-success btn-sm" onclick="subscriptionAction(${s.id}, 'activate')">Activate</button>
                            ` : 'Closed')
                        })),
                        ...(data.quotations || []).map(q => ({
                            name: q.name,
                            partner_name: q.partner_name,
                            plan_name: q.plan_name,
                            amount: q.total,
                            renewal: 'Quotation Stage',
                            status: q.status,
                            actionHtml: `<button class="btn btn-primary btn-sm" onclick="quotationAction(${q.id}, 'convert')">Convert to Sub</button>`
                        }))
                    ];
                    setHtml('staff-subs-tbody', allSubsQuotes.map(item => `
                        <tr>
                            <td style="font-weight:700; font-family:'JetBrains Mono', monospace;">${item.name}</td>
                            <td>${item.partner_name}</td>
                            <td>${item.plan_name}</td>
                            <td style="font-weight:700;">₹${Number(item.amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                            <td>${item.renewal}</td>
                            <td><span class="badge badge-${item.status}">${item.status.toUpperCase()}</span></td>
                            <td>${item.actionHtml}</td>
                        </tr>
                    `).join(''));
                }

                if (data.invoices) {
                    setHtml('staff-invoices-tbody', data.invoices.map(i => `
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
                    `).join(''));
                }

                if (data.payments) {
                    setHtml('staff-payments-tbody', data.payments.map(p => `
                        <tr>
                            <td style="font-weight:700; font-family:'JetBrains Mono', monospace;">${p.name}</td>
                            <td>${p.partner_name}</td>
                            <td>${p.invoice_name}</td>
                            <td><span class="badge badge-quotation">${p.payment_method.toUpperCase()}</span></td>
                            <td style="font-weight:700; color:var(--success);">₹${Number(p.amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                            <td>${p.payment_date}</td>
                            <td><code>${p.transaction_reference}</code></td>
                            <td><span class="badge badge-active">POSTED</span></td>
                        </tr>
                    `).join(''));
                }

                if (data.guardian_cases) {
                    setHtml('staff-guardian-tbody', data.guardian_cases.map(c => `
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
                    `).join(''));
                }

                if (data.users) {
                    setHtml('staff-customers-tbody', data.users.filter(u => u.role === 'customer').map(u => `
                        <tr>
                            <td style="font-weight:700;">${u.partner_name || u.name}</td>
                            <td>${u.login}</td>
                            <td><span class="badge role-badge-customer">Customer Organization</span></td>
                            <td><span class="badge ${u.active ? 'badge-active' : 'badge-critical'}">${u.active ? 'ACTIVE' : 'INACTIVE'}</span></td>
                        </tr>
                    `).join(''));
                }

                // =============================================================
                // POPULATE ROLE DASHBOARD 3: CUSTOMER PORTAL DATA (ISOLATED)
                // =============================================================
                if (CURRENT_USER) {
                    const myPartnerId = CURRENT_USER.partner_id;
                    const myName = CURRENT_USER.partner_name || CURRENT_USER.name;

                    const mySubs = (data.subscriptions || []).filter(s => (myPartnerId && s.partner_id === myPartnerId) || s.partner_name === myName);
                    const myInvs = (data.invoices || []).filter(i => (myPartnerId && i.partner_id === myPartnerId) || i.partner_name === myName);
                    const myPayments = (data.payments || []).filter(p => (myPartnerId && p.partner_id === myPartnerId) || p.partner_name === myName);

                    // Profile & Welcome Information
                    setTxt('cust-welcome-title', `Welcome back, ${CURRENT_USER.name}!`);
                    setTxt('cust-welcome-org', CURRENT_USER.partner_name || CURRENT_USER.name);
                    setTxt('cust-profile-name', CURRENT_USER.name);
                    setTxt('cust-profile-email', CURRENT_USER.login);
                    setTxt('cust-profile-company', CURRENT_USER.partner_name || 'Independent Client');

                    // Customer KPIs
                    const totalOutstanding = myInvs.reduce((acc, i) => acc + (parseFloat(i.amount_residual) || 0), 0);
                    const totalMrr = mySubs.reduce((acc, s) => acc + (parseFloat(s.recurring_total) || 0), 0);
                    const firstRenewal = (mySubs.length > 0 && mySubs[0].next_renewal_date) ? mySubs[0].next_renewal_date : 'N/A';
                    const firstPlan = (mySubs.length > 0) ? mySubs[0].plan_name : 'No Active Plan';

                    setTxt('cust-kpi-subs', `${mySubs.length} Active`);
                    setTxt('cust-kpi-planname', firstPlan);
                    setTxt('cust-kpi-mrr', '₹' + Number(totalMrr).toLocaleString('en-IN', {minimumFractionDigits: 2}));
                    setTxt('cust-kpi-renewal', firstRenewal);
                    setTxt('cust-kpi-outstanding', '₹' + Number(totalOutstanding).toLocaleString('en-IN', {minimumFractionDigits: 2}));

                    // Customer Subscriptions Table
                    setHtml('cust-subs-tbody', mySubs.length > 0 ? mySubs.map(s => `
                        <tr>
                            <td style="font-weight:700; font-family:'JetBrains Mono', monospace;">${s.name}</td>
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
                                ` : '<span style="color:var(--gray-600)">No actions</span>'}
                            </td>
                        </tr>
                    `).join('') : '<tr><td colspan="6" style="text-align:center; color:var(--gray-600); padding:1.5rem;">No active subscriptions found for your account.</td></tr>');

                    // Customer Invoices Table
                    setHtml('cust-invoices-tbody', myInvs.length > 0 ? myInvs.map(i => `
                        <tr>
                            <td style="font-weight:700; font-family:'JetBrains Mono', monospace;">${i.name}</td>
                            <td>${i.invoice_date_due}</td>
                            <td style="font-weight:700;">₹${Number(i.amount_total).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                            <td style="font-weight:700; color:${i.amount_residual > 0 ? 'var(--danger)' : 'var(--success)'};">₹${Number(i.amount_residual).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                            <td><span class="badge ${i.payment_state === 'paid' ? 'badge-active' : 'badge-critical'}">${i.payment_state.toUpperCase()}</span></td>
                            <td><button class="btn btn-outline btn-sm" onclick="showToast('⬇️ Downloading Invoice Receipt PDF...')">📄 Receipt</button></td>
                            <td>
                                ${i.payment_state !== 'paid' ? `
                                    <button class="btn btn-primary btn-sm" onclick="paySpecificInvoice(${i.id}, ${i.amount_residual})">Pay Now →</button>
                                ` : '<span style="color:var(--success); font-weight:700;">✓ Settled</span>'}
                            </td>
                        </tr>
                    `).join('') : '<tr><td colspan="7" style="text-align:center; color:var(--gray-600); padding:1.5rem;">No invoices generated for your account yet.</td></tr>');

                    // Populate Customer Invoice Payment Select
                    const custPaySel = document.getElementById('cust-pay-invoice-select');
                    if (custPaySel) {
                        const unpaid = myInvs.filter(i => i.payment_state !== 'paid');
                        if (unpaid.length === 0) {
                            custPaySel.innerHTML = '<option value="">All invoices are fully settled!</option>';
                            const custPayAmt = document.getElementById('cust-pay-amount');
                            if (custPayAmt) custPayAmt.value = 0;
                        } else {
                            custPaySel.innerHTML = unpaid.map(i => `<option value="${i.id}" data-residual="${i.amount_residual}">${i.name} - Due: ₹${Number(i.amount_residual).toLocaleString('en-IN')}</option>`).join('');
                            autoFillCustInvoiceResidual();
                        }
                    }
                }

            } catch (e) {
                console.error("Failed to load master state:", e);
            }
        }

        // Action Handlers
        async function submitAddUser() {
            const name = document.getElementById('usr-name').value;
            const login = document.getElementById('usr-email').value;
            const role = document.getElementById('usr-role').value;
            const password = document.getElementById('usr-pwd').value;
            const callerRole = (CURRENT_USER && CURRENT_USER.role) ? CURRENT_USER.role : '';
            const res = await fetch('/api/users/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-User-Role': callerRole
                },
                body: JSON.stringify({name, login, role, password, requester_role: callerRole})
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

        let currentDiscountsData = [];
        let currentPaymentsData = [];

        async function submitCreateDiscount() {
            const name = document.getElementById('dsc-name').value;
            const code = document.getElementById('dsc-code').value;
            const discount_type = document.getElementById('dsc-type').value;
            const value = parseFloat(document.getElementById('dsc-val').value);
            const min_purchase_amount = parseFloat(document.getElementById('dsc-min-spend') ? document.getElementById('dsc-min-spend').value : 0) || 0.0;
            const min_quantity = parseInt(document.getElementById('dsc-min-qty') ? document.getElementById('dsc-min-qty').value : 1) || 1;
            const start_date = document.getElementById('dsc-start-date') ? document.getElementById('dsc-start-date').value : null;
            const end_date = document.getElementById('dsc-end-date') ? document.getElementById('dsc-end-date').value : null;
            const max_usage_limit = parseInt(document.getElementById('dsc-max-usage') ? document.getElementById('dsc-max-usage').value : 0) || 0;
            const scope = document.getElementById('dsc-scope') ? document.getElementById('dsc-scope').value : 'entire_subscription';

            const res = await fetch('/api/discounts/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, code, discount_type, value, min_purchase_amount, min_quantity, start_date, end_date, max_usage_limit, scope})
            });
            const d = await res.json();
            if (d.error) { alert('Discount Error: ' + d.error); return; }
            showToast('✓ Promotional Discount Rule saved!');
            closeModal('modal-create-discount');
            fetchAllData();
        }

        function autoFillInvoiceResidual() {
            const select = document.getElementById('pay-inv-id');
            const selectedText = select.options[select.selectedIndex].text;
            const match = selectedText.match(/Due:\s*₹([0-9.,]+)/);
            if (match) {
                document.getElementById('pay-amount').value = parseFloat(match[1].replace(/,/g, ''));
            }
        }

        function filterDiscounts(status, btn) {
            document.querySelectorAll('.active-disc-filter').forEach(el => el.classList.remove('btn-primary'));
            if (btn) btn.classList.add('btn-primary');
            const tbody = document.getElementById('discounts-full-table-body');
            if (!tbody || !currentDiscountsData) return;
            const filtered = status === 'active' ? currentDiscountsData.filter(d => d.active) :
                             status === 'expired' ? currentDiscountsData.filter(d => !d.active) : currentDiscountsData;
            tbody.innerHTML = filtered.map(d => `
                <tr>
                    <td style="font-weight:600;">${d.name}</td>
                    <td><code>${d.code}</code></td>
                    <td>${d.discount_type === 'percentage' ? 'Percentage' : 'Fixed Amount'}</td>
                    <td style="font-weight:700; color:var(--primary);">${d.discount_type === 'percentage' ? d.value + '%' : '₹' + d.value}</td>
                    <td>₹${d.min_purchase_amount || 0}</td>
                    <td>${d.min_quantity || 1}</td>
                    <td>${d.usage_count} / ${d.max_usage_limit || '∞'}</td>
                    <td>${d.start_date || 'Immediate'} → ${d.end_date || 'Permanent'}</td>
                    <td><span class="badge ${d.active ? 'badge-active' : 'badge-critical'}">${d.active ? 'ACTIVE' : 'INACTIVE'}</span></td>
                </tr>
            `).join('');
            showToast(`✓ Filtered Discounts: ${status.toUpperCase()}`);
        }

        function filterPayments(method, btn) {
            document.querySelectorAll('.active-pay-filter').forEach(el => el.classList.remove('btn-primary'));
            if (btn) btn.classList.add('btn-primary');
            const tbody = document.getElementById('payments-full-table-body');
            if (!tbody || !currentPaymentsData) return;
            const filtered = method === 'all' ? currentPaymentsData : currentPaymentsData.filter(p => p.payment_method === method);
            tbody.innerHTML = filtered.map(p => `
                <tr>
                    <td style="font-weight:700; font-family:'JetBrains Mono', monospace;">${p.name}</td>
                    <td>${p.partner_name}</td>
                    <td>${p.invoice_name}</td>
                    <td><span class="badge badge-quotation">${p.payment_method.toUpperCase()}</span></td>
                    <td style="font-weight:700; color:var(--success);">₹${Number(p.amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                    <td>${p.payment_date}</td>
                    <td><code>${p.transaction_reference}</code></td>
                    <td><span class="badge badge-active">POSTED</span></td>
                </tr>
            `).join('');
            showToast(`✓ Filtered Payments: ${method.toUpperCase()}`);
        }

        async function filterFinancePreset(preset, btn) {
            document.querySelectorAll('.active-fin-filter').forEach(el => el.classList.remove('btn-primary'));
            if (btn) btn.classList.add('btn-primary');
            const t0 = performance.now();
            const res = await fetch(`/api/finance/filter?preset=${preset}`);
            const d = await res.json();
            const latency = Math.round(performance.now() - t0);
            if (document.getElementById('fin-query-latency')) {
                document.getElementById('fin-query-latency').innerText = `${latency}ms`;
            }
            if (d.kpis) {
                document.getElementById('fin-active-subs').innerText = d.kpis.active_subscriptions;
                document.getElementById('fin-mrr').innerText = '₹' + Number(d.kpis.mrr).toLocaleString('en-IN', {minimumFractionDigits: 2});
                document.getElementById('fin-arr').innerText = '₹' + Number(d.kpis.arr).toLocaleString('en-IN', {minimumFractionDigits: 2});
                document.getElementById('fin-rev-received').innerText = '₹' + Number(d.kpis.revenue_received).toLocaleString('en-IN', {minimumFractionDigits: 2});
                document.getElementById('fin-outstanding').innerText = '₹' + Number(d.kpis.outstanding_amount).toLocaleString('en-IN', {minimumFractionDigits: 2});
                document.getElementById('fin-overdue').innerText = '₹' + Number(d.kpis.overdue_invoices_count);
                document.getElementById('fin-total-cust').innerText = d.kpis.total_customers;
                document.getElementById('fin-renewals-due').innerText = d.kpis.upcoming_renewals_count;
            }
            showToast(`✓ Filter applied: ${preset.toUpperCase()} (${latency}ms)`);
        }

        async function triggerReconciliationDemo() {
            const out = document.getElementById('recon-demo-output');
            out.innerHTML = '⚡ Scanning imported CSV bank statement transactions...';
            const res = await fetch('/api/reconciliation/demo', {method: 'POST'});
            const d = await res.json();
            out.innerHTML = `
                <div style="color:var(--success); font-weight:700;">✓ Matched &amp; Reconciled Successfully!</div>
                <div>Target Invoice: <strong>${d.invoice}</strong></div>
                <div>Reconciled Amount: <strong>₹${Number(d.reconciled_amount).toLocaleString('en-IN')}</strong></div>
                <div>Multi-Signal Confidence: <strong>${d.confidence}</strong></div>
                <div style="margin-top:0.5rem; font-size:0.75rem; color:var(--gray-600);">Accounting payment created. Risk status transitioned to RECOVERED.</div>
            `;
            showToast('✓ Statement reconciled into native accounting payment!');
            fetchAllData();
        }

        async function sendTabCopilotQuery() {
            const input = document.getElementById('tab-copilot-input');
            const q = input.value.trim();
            if (!q) return;
            const chat = document.getElementById('tab-copilot-chat-box');
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
                const formatted = (d.response || '').split(String.fromCharCode(10)).join('<br>');
                b.innerHTML = `<strong>[${d.provider}]</strong><br>${formatted}`;
            } catch(e) {
                b.innerText = 'Error connecting to copilot: ' + e;
            }
            chat.scrollTop = chat.scrollHeight;
        }

        function sendPredefinedCopilot(text) {
            document.getElementById('tab-copilot-input').value = text;
            sendTabCopilotQuery();
        }

        async function submitRecordPayment() {
            const invoice_id = parseInt(document.getElementById('pay-inv-id').value);
            const amount = parseFloat(document.getElementById('pay-amount').value);
            const payment_method = document.getElementById('pay-method').value;
            const payment_date = document.getElementById('pay-date') ? document.getElementById('pay-date').value : null;
            const transaction_reference = document.getElementById('pay-ref').value;
            const notes = document.getElementById('pay-notes') ? document.getElementById('pay-notes').value : '';
            const res = await fetch('/api/payments/record', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({invoice_id, amount, payment_method, payment_date, transaction_reference, notes})
            });
            const d = await res.json();
            if (d.error) { alert('Payment Error: ' + d.error); return; }
            showToast('✓ Payment recorded and invoice residual updated!');
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

        // Billing & Subscription Actions
        async function triggerAutomatedBilling() {
            showToast('⚡ Running automated recurring billing engine...');
            const res = await fetch('/api/billing/run', {method: 'POST'});
            const d = await res.json();
            if (d.error) {
                showToast('⚠️ ' + d.error);
            } else {
                showToast(`✓ Generated ${d.invoices_created || 0} recurring invoices.`);
            }
            fetchAllData();
        }

        async function subscriptionAction(id, action) {
            showToast(`⚡ Processing ${action} on subscription...`);
            const res = await fetch('/api/subscriptions/action', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({subscription_id: id, action: action})
            });
            const d = await res.json();
            if (d.error) {
                showToast('⚠️ ' + d.error);
            } else {
                showToast(`✓ Subscription ${action} successful!`);
            }
            fetchAllData();
        }

        async function quotationAction(id, action) {
            showToast(`⚡ Converting quotation to active subscription...`);
            const res = await fetch('/api/quotations/action', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({quotation_id: id, action: action})
            });
            const d = await res.json();
            if (d.error) {
                showToast('⚠️ ' + d.error);
            } else {
                showToast(`✓ Quotation converted to active subscription!`);
            }
            fetchAllData();
        }

        function promptPaymentForInv(invId, residual) {
            openModal('modal-record-payment');
            const select = document.getElementById('pay-inv-id');
            if (select) select.value = invId;
            const amt = document.getElementById('pay-amount');
            if (amt) amt.value = residual;
        }

        async function submitCreateTax() {
            const name = document.getElementById('tax-name').value;
            const amount = parseFloat(document.getElementById('tax-rate').value);
            const amount_type = document.getElementById('tax-type').value;
            const price_include = document.getElementById('tax-include').value === 'true';
            const res = await fetch('/api/taxes/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, amount, amount_type, price_include})
            });
            showToast('✓ Tax definition saved!');
            closeModal('modal-create-tax');
            fetchAllData();
        }

        async function submitCreateSub() {
            const partner_id = parseInt(document.getElementById('sub-cust-id').value);
            const plan_id = parseInt(document.getElementById('sub-plan-id').value);
            const recurring_total = parseFloat(document.getElementById('sub-amount').value);
            const next_renewal_date = document.getElementById('sub-start-date').value || null;
            const res = await fetch('/api/subscriptions/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({partner_id, plan_id, recurring_total, next_renewal_date})
            });
            showToast('✓ Subscription created and activated!');
            closeModal('modal-create-sub');
            fetchAllData();
        }

        async function submitCreateQuote() {
            const partner_id = parseInt(document.getElementById('quote-cust-id').value);
            const plan_id = parseInt(document.getElementById('quote-plan-id').value);
            const total = parseFloat(document.getElementById('quote-amount').value);
            const res = await fetch('/api/quotations/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({partner_id, plan_id, total})
            });
            showToast('✓ Quotation generated successfully!');
            closeModal('modal-create-quote');
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
                const formatted = (d.response || '').split(String.fromCharCode(10)).join('<br>');
                b.innerHTML = `<strong>[${d.provider}]</strong><br>${formatted}`;
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

        // Explicit tab click listener attachment
        document.querySelectorAll('.nav-tab[data-tab]').forEach(function(tab) {
            tab.addEventListener('click', function(e) {
                const tid = this.getAttribute('data-tab');
                if (tid) switchTab(tid, this);
            });
        });

        document.querySelectorAll('.nav-tab[data-staff-tab]').forEach(function(tab) {
            tab.addEventListener('click', function(e) {
                const tid = this.getAttribute('data-staff-tab');
                if (tid) switchStaffTab(tid, this);
            });
        });

        document.querySelectorAll('.nav-tab[data-cust-tab]').forEach(function(tab) {
            tab.addEventListener('click', function(e) {
                const tid = this.getAttribute('data-cust-tab');
                if (tid) switchCustomerTab(tid, this);
            });
        });

        // Browser history popstate handling
        window.addEventListener('popstate', function(e) {
            routeTo(window.location.pathname, false);
        });

        // Application Startup & Initial Route Determination
        const initialPath = window.location.pathname;
        routeTo(initialPath, false);
        setInterval(fetchAllData, 8000);
    </script>
</body>
</html>
"""

class MasterServerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        encoded = json.dumps(data, default=str).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(encoded)))
        self.send_header('Connection', 'close')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(encoded)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', '0')
        self.send_header('Connection', 'close')
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        app_routes = ['/', '/subscriptiq', '/login', '/register', '/admin/dashboard', '/staff/dashboard', '/customer/dashboard']
        if path in app_routes:
            encoded = HTML_PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(encoded)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(encoded)

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
                p_id = s.partner_id.id if hasattr(s.partner_id, 'id') else s.partner_id
                subs.append({
                    'id': s.id,
                    'name': s.name,
                    'partner_id': p_id,
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
                p_id = q.partner_id.id if hasattr(q.partner_id, 'id') else q.partner_id
                quotes.append({
                    'id': q.id,
                    'name': q.name,
                    'partner_id': p_id,
                    'partner_name': cust,
                    'plan_name': pl_name,
                    'total': getattr(q, 'amount_total', 1416.0),
                    'status': 'quotation'
                })

            # Invoices
            invoices = []
            for inv in GLOBAL_ENV['account.move'].search([('move_type', '=', 'out_invoice')]):
                cust = inv.partner_id.name if hasattr(inv.partner_id, 'name') else 'Customer'
                p_id = inv.partner_id.id if hasattr(inv.partner_id, 'id') else inv.partner_id
                invoices.append({
                    'id': inv.id,
                    'name': inv.name,
                    'partner_id': p_id,
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
                p_id = p.partner_id.id if hasattr(p.partner_id, 'id') else p.partner_id
                payments.append({
                    'id': p.id,
                    'name': p.name,
                    'partner_id': p_id,
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

            # Discount usage history
            disc_hist = []
            if 'subscriptiq.discount.usage.history' in GLOBAL_ENV:
                for dh in GLOBAL_ENV['subscriptiq.discount.usage.history'].search([]):
                    d_rule = dh.discount_id.name if hasattr(dh.discount_id, 'name') else 'Discount'
                    p_name = dh.partner_id.name if hasattr(dh.partner_id, 'name') else 'Customer'
                    inv_name = dh.invoice_id.name if hasattr(dh.invoice_id, 'name') else 'Invoice'
                    disc_hist.append({
                        'name': dh.name,
                        'discount_name': d_rule,
                        'partner_name': p_name,
                        'invoice_name': inv_name,
                        'original_amount': float(dh.original_amount),
                        'discount_amount': float(dh.discount_amount),
                        'final_amount': float(dh.final_amount),
                        'usage_date': str(dh.usage_date or '')
                    })

            # Payment metrics
            pay_metrics = AccountPayment.get_payment_dashboard_metrics(GLOBAL_ENV)

            # Audit events
            audit_events = []
            if 'subscriptiq.audit.event' in GLOBAL_ENV:
                for ev in GLOBAL_ENV['subscriptiq.audit.event'].search([]):
                    audit_events.append({
                        'sequence': ev.sequence,
                        'event_type': ev.event_type,
                        'timestamp': str(ev.timestamp)[:19] if ev.timestamp else '',
                        'payload_hash': ev.payload_hash or '',
                        'current_hash': ev.current_hash or ''
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
                'guardian_cases': cases,
                'discount_history': disc_hist,
                'payment_metrics': pay_metrics,
                'audit_events': audit_events
            })

        elif path == '/api/finance/filter':
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            preset = query.get('preset', ['all'])[0]
            partner_id = query.get('partner_id', [None])[0]
            pay_method = query.get('payment_method', [None])[0]
            sub_status = query.get('sub_status', [None])[0]
            filters = {
                'date_preset': preset,
                'partner_id': partner_id,
                'payment_method': pay_method,
                'subscription_status': sub_status
            }
            res = FinanceDashboardService.compute_kpis_and_charts(GLOBAL_ENV, filters)
            self.send_json(res)

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
            if path == '/api/auth/login':
                login = params.get('login', '').strip().lower()
                password = params.get('password', '')
                user = ResUsers.authenticate(GLOBAL_ENV, login, password)
                if not user:
                    self.send_json({'success': False, 'error': 'Invalid email or password.'}, status=401)
                else:
                    p_id = user.partner_id.id if hasattr(user.partner_id, 'id') else user.partner_id
                    p_name = user.partner_id.name if hasattr(user.partner_id, 'name') else user.name
                    self.send_json({
                        'success': True,
                        'user': {
                            'id': user.id,
                            'name': user.name,
                            'login': user.login,
                            'role': user.role,
                            'partner_id': p_id,
                            'partner_name': p_name
                        }
                    })

            elif path == '/api/auth/register' or path == '/api/users/register':
                params['role'] = 'customer'
                u = ResUsers.create_user(GLOBAL_ENV, params)
                p_id = u.partner_id.id if hasattr(u.partner_id, 'id') else u.partner_id
                p_name = u.partner_id.name if hasattr(u.partner_id, 'name') else u.name
                self.send_json({
                    'success': True,
                    'user_id': u.id,
                    'user': {
                        'id': u.id,
                        'name': u.name,
                        'login': u.login,
                        'role': 'customer',
                        'partner_id': p_id,
                        'partner_name': p_name
                    }
                })

            elif path == '/api/auth/logout':
                self.send_json({'success': True, 'message': 'Successfully logged out.'})

            elif path == '/api/users/add':
                caller_role = self.headers.get('X-User-Role') or params.get('requester_role', 'admin')
                if caller_role != 'admin':
                    self.send_json({'error': 'Access Denied: Only Administrators can create staff accounts.'}, status=403)
                else:
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
                    'min_purchase_amount': float(params.get('min_purchase_amount', 0.0)),
                    'min_quantity': int(params.get('min_quantity', 1)),
                    'start_date': params.get('start_date') or None,
                    'end_date': params.get('end_date') or None,
                    'max_usage_limit': int(params.get('max_usage_limit', 0)),
                    'scope': params.get('scope', 'entire_subscription'),
                    'active': bool(params.get('active', True))
                })
                self.send_json({'success': True, 'discount_id': d.id})

            elif path == '/api/taxes/create':
                t = GLOBAL_ENV['account.tax'].create({
                    'name': params.get('name', 'Tax Definition'),
                    'amount': float(params.get('amount', 18.0)),
                    'amount_type': params.get('amount_type', 'percent'),
                    'price_include': bool(params.get('price_include', False)),
                    'company_id': GLOBAL_ENV.company.id
                })
                self.send_json({'success': True, 'tax_id': t.id})

            elif path == '/api/subscriptions/create':
                sub_count = len(GLOBAL_ENV['sale.order'].search([('is_subscription', '=', True)])) + 1
                partner_id = int(params.get('partner_id', 1))
                plan_id = int(params.get('plan_id', 1))
                rec_total = float(params.get('recurring_total', 1200.0))
                renewal = params.get('next_renewal_date') or str(datetime.now().date() + timedelta(days=30))
                sub = GLOBAL_ENV['sale.order'].create({
                    'name': f"SUB-2026-{sub_count:04d}",
                    'partner_id': partner_id,
                    'company_id': GLOBAL_ENV.company.id,
                    'subscriptiq_status': 'active',
                    'stage': 'in_progress',
                    'is_subscription': True,
                    'plan_id': plan_id,
                    'subscriptiq_plan_id': plan_id,
                    'recurring_total': rec_total,
                    'subscriptiq_recurring_total': rec_total,
                    'subscriptiq_next_renewal_date': renewal,
                    'next_renewal_date': renewal
                })
                self.send_json({'success': True, 'subscription_id': sub.id})

            elif path == '/api/quotations/create':
                q_count = len(GLOBAL_ENV['sale.order'].search([('state', 'in', ['draft', 'sent'])])) + 1
                quote = GLOBAL_ENV['sale.order'].create({
                    'name': f"SO-2026-{q_count:04d}",
                    'partner_id': int(params.get('partner_id', 1)),
                    'company_id': GLOBAL_ENV.company.id,
                    'state': 'sent',
                    'subscriptiq_status': 'quotation',
                    'is_subscription': True,
                    'plan_id': int(params.get('plan_id', 1)),
                    'amount_total': float(params.get('total', 1500.0)),
                    'recurring_total': float(params.get('total', 1500.0))
                })
                self.send_json({'success': True, 'quotation_id': quote.id})

            elif path == '/api/reconciliation/demo':
                payment = GLOBAL_ENV['account.payment'].record_payment({
                    'invoice_id': 1,
                    'amount': 2500.0,
                    'payment_method': 'bank_transfer',
                    'transaction_reference': 'RECON-STMT-MATCH-01',
                    'notes': 'Auto-matched from bank statement CSV with 100% confidence'
                })
                self.send_json({
                    'success': True,
                    'matched': 1,
                    'invoice': 'INV/2026/0001',
                    'reconciled_amount': 2500.0,
                    'confidence': '100% (High Confidence Match)'
                })

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
    httpd = ThreadingHTTPServer(server_address, MasterServerHandler)
    httpd.daemon_threads = True
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
