# -*- coding: utf-8 -*-
{
    'name': 'SubscriptIQ Revenue Guardian',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Revenue Assurance',
    'summary': 'AI-ready Revenue Assurance & Duplicate Billing Guard for Odoo 19',
    'description': """
SubscriptIQ - Module 1: Revenue Guardian
========================================
A comprehensive revenue assurance and billing integrity engine integrated into Odoo 19.

Key Features:
-------------
* **Revenue Integrity Scanning**:
  - Automatically flags overdue customer invoices with aging metrics.
  - Monitors upcoming payment deadlines and detects impending default risks.
  - Identifies excessive or suspicious invoice line discounts (> 25%).
  - Detects billing amount discrepancies and currency / total mismatches.
  - Maintains complete historical logs and scan metrics.

* **Risk Case Management**:
  - Automatically provisions prioritized risk cases (Low, Medium, High, Critical).
  - Full lifecycle workflow: New -> Investigating -> Resolved / Dismissed.
  - Directly linked to standard native models (`res.partner`, `account.move`).
  - Records actionable recommendations and calculated financial exposure.

* **Duplicate Billing Protection**:
  - Dedicated Billing Guard with PostgreSQL-level uniqueness constraints.
  - Prevents race conditions and double charges across subscription cycles and companies.
  - Two-phase billing reservation workflow (Reserved -> Invoiced / Cancelled).

* **Automation & Cron**:
  - Pre-configured automated scheduled actions.
  - Manual on-demand scan triggers with security controls.
    """,
    'author': 'SubscriptIQ Team',
    'website': 'https://github.com/subscriptiq/subscriptiq_guardian',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'sale_management',
    ],
    'data': [
        'security/subscriptiq_security.xml',
        'security/ir.model.access.csv',
        'data/guardian_cron.xml',
        'views/guardian_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
