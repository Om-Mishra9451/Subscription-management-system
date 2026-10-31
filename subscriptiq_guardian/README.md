# SubscriptIQ - Module 1: Revenue Guardian (`subscriptiq_guardian`)

An AI-ready Revenue Assurance and Duplicate Billing Prevention addon designed for **Odoo 19**.

---

## 1. Overview & Architecture

**SubscriptIQ** safeguards Odoo recurring and standard billing workflows against revenue leakage, rogue discounts, overdue customer defaults, calculation discrepancies, and race-condition double billing.

### Core Modules & Models
1. **Revenue Audit Scanner (`subscriptiq.guardian.scan`)**:
   - Executes multi-vector audits across customer receivables (`account.move`, `account.move.line`).
   - Identifies overdue accounts, impending due dates (7-day horizon), excessive discounts (>25%), and invoice header/tax balance discrepancies.
   - Logs execution metrics, count of affected records, and total financial exposure.
2. **Risk Case Tracker (`subscriptiq.guardian.risk.case`)**:
   - Triage engine with severity weighting (`critical`, `high`, `medium`, `low`).
   - Complete lifecycle: `New` -> `Investigating` -> `Resolved` / `Dismissed`.
   - Links directly to standard Odoo models (`res.partner`, `account.move`) without duplicating data.
3. **Duplicate Billing Guard (`subscriptiq.billing.guard`)**:
   - High-concurrency protection engine with PostgreSQL unique constraint: `unique(subscription_ref, period_start, period_end, company_id)`.
   - Pre-reservation API (`reserve_billing_period`) to safely lock subscription periods before generating invoices.
   - Post-billing linkage (`action_link_invoice`) to bind the generated invoice and seal the billing cycle.
4. **Audit Rules (`subscriptiq.guardian.rule`)**:
   - Configurable rules defining thresholds for discount limits, aging horizons, and default severities.

---

## 2. Requirements & Compatibility

- **Odoo**: Version 19.0 (Community or Enterprise).
- **Python**: 3.10+
- **Database**: PostgreSQL 14+
- **Odoo Standard Dependencies**:
  - `base`
  - `account`
  - `sale_management`
- **Zero Enterprise-only hard locks**: Works completely on standard Odoo models without forcing `sale_subscription`.

---

## 3. Installation Guide

1. Place the `subscriptiq_guardian` directory into your custom Odoo addons path (e.g. `/opt/odoo/custom-addons/subscriptiq_guardian`).
2. Update the `addons_path` in your `odoo.conf`:
   ```ini
   addons_path = /path/to/odoo/addons,/path/to/custom-addons
   ```
3. Restart your Odoo 19 server:
   ```bash
   sudo systemctl restart odoo
   # or via terminal
   ./odoo-bin -c odoo.conf
   ```
4. Update the app list in Odoo:
   - Activate **Developer Mode** under Settings.
   - Navigate to **Apps -> Update Apps List**.
   - Search for `subscriptiq_guardian` or `SubscriptIQ Revenue Guardian`.
   - Click **Activate**.

---

## 4. Odoo Configuration & Security

- **User Groups**:
  - `SubscriptIQ / Guardian User`: Read access to rules, scans, risk cases, and billing guard entries. Can investigate cases.
  - `SubscriptIQ / Guardian Manager`: Full administrative rights, ability to trigger scans, configure rules, and manage all records.
- **Multi-Company**: Multi-company record rules ensure isolation across company branches.
- **Automated Cron**:
  - An automated scheduled action (`SubscriptIQ: Automated Revenue Assurance Scan`) is enabled to run daily by default. Configurable in **Settings -> Technical -> Automation -> Scheduled Actions**.

---

## 5. Usage & Example Workflows

### Manual Revenue Audit
1. Navigate to **SubscriptIQ -> Revenue Guardian -> Revenue Scans**.
2. Click **New** and press **Execute Audit Scan**.
3. The engine parses posted invoices, calculates aging, inspects discounts, and automatically creates linked **Risk Cases**.
4. View the generated list under **Risk Cases** to investigate and resolve issues.

### Integrating Duplicate Billing Guard in Python Code
When writing custom recurring billing scripts or webhooks, wrap invoice generation with `subscriptiq.billing.guard`:

```python
# 1. Acquire billing reservation
guard_obj = env['subscriptiq.billing.guard']
try:
    reservation = guard_obj.reserve_billing_period(
        subscription_ref="SUB-2026-001",
        period_start="2026-11-01",
        period_end="2026-11-30",
        partner_id=partner.id,
        company_id=env.company.id,
        expected_amount=250.00
    )
except Exception as e:
    # Duplicate detected! Handled safely and logged into Risk Cases automatically
    _logger.warning("Duplicate billing rejected: %s", str(e))
    return

# 2. Proceed with native invoice creation
invoice = env['account.move'].create({
    'move_type': 'out_invoice',
    'partner_id': partner.id,
    'invoice_line_ids': [...],
})

# 3. Link invoice to seal reservation
reservation.action_link_invoice(invoice)
```

---

## 6. Testing Instructions

Run the Odoo test runner or run via CLI:
```bash
odoo-bin -c odoo.conf -d test_db -u subscriptiq_guardian --test-enable --stop-after-init
```
