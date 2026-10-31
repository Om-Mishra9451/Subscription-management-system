# -*- coding: utf-8 -*-
{
    'name': 'SubscriptIQ — Autonomous Revenue Assurance for Odoo',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Subscription',
    'summary': 'Autonomous Revenue Assurance Engine for Odoo. Tagline: Detect. Prevent. Recover. Measure.',
    'description': """
SubscriptIQ: Autonomous Revenue Assurance for Odoo
==================================================
Protects businesses from revenue leakage across the complete subscription-to-cash lifecycle:
- Continuous Revenue Guardian monitoring engine with deterministic rule evaluations
- Transactional duplicate billing prevention guard locks
- Deterministic bank payment reconciliation engine (0.50/0.30/0.15/0.05 weighting)
- Verified Revenue Recovered tracking grounded in native accounting payments
- Explainable customer risk intelligence with local Scikit-Learn ML pipeline
- Free-tier AI Finance Copilot with multi-provider fallback (Groq -> Gemini -> OpenRouter)
- Cryptographic SHA-256 tamper-evident audit ledger
    """,
    'author': 'Brightloop Software / Antigravity Team',
    'website': 'https://brightloop.software/subscriptiq',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale_management',
        'account',
        'mail',
        'portal',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/sequences.xml',
        'data/default_rules.xml',
        'data/scheduled_actions.xml',
        'data/mail_templates.xml',
        'views/dashboard_views.xml',
        'views/scan_views.xml',
        'views/risk_case_views.xml',
        'views/rule_views.xml',
        'views/recovery_views.xml',
        'views/payment_import_views.xml',
        'views/audit_views.xml',
        'views/settings_views.xml',
        'views/templates.xml',
        'views/menu.xml',
        'report/revenue_risk_report.xml',
        'report/revenue_risk_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'subscriptiq/static/src/css/subscriptiq_theme.css',
            'subscriptiq/static/src/js/subscriptiq_copilot.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
