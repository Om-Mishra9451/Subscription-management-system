# SubscriptIQ — Architectural Design Document
## Autonomous Revenue Assurance Engine for Odoo

---

## 1. System Philosophy & Objectives

Modern subscription software companies lose 3% to 8% of Annual Recurring Revenue (ARR) to silent operational friction:
- Unrenewed subscriptions continuing service without billing.
- Concurrent scheduler runs generating duplicate invoices.
- Expired or over-allocated promotional discounts applied to renewals.
- Unmatched bank transfer deposits languishing in clearing accounts while customer accounts are marked overdue.
- Arbitrary manual status changes marking invoices paid without accounting proof.

**SubscriptIQ** acts as a non-invasive, continuous intelligence and protection layer on top of native Odoo business applications. Odoo remains the source of truth for accounts, journals, and orders. SubscriptIQ actively guarantees that every rupee owed is billed accurately, collected, matched, and verified.

---

## 2. Layered Architecture

SubscriptIQ is structured into clean separation-of-concerns layers:

```
+------------------------------------------------------------------------+
| 1. PRESENTATION LAYER (XML Views, OWL Widgets, Indigo Theme CSS)        |
|    - Revenue Command Center (KPIs, Charts)                             |
|    - Revenue Guardian (Risk Investigation, Evidence Cards)              |
|    - Smart Reconciliation (Two-Panel Side-by-Side Matching)            |
|    - AI Copilot Interface (Grounded Dialogue with Action Previews)     |
+------------------------------------------------------------------------+
                                   |
+------------------------------------------------------------------------+
| 2. CONTROLLERS & WIZARDS                                               |
|    - CopilotController: /subscriptiq/copilot/ask                       |
|    - BankImportWizard: CSV validation, batch upload, candidate scoring |
|    - ActionApprovalWizard: Dual authorization interface                |
+------------------------------------------------------------------------+
                                   |
+------------------------------------------------------------------------+
| 3. CORE SERVICE LAYER                                                  |
|    - RevenueCalculator: Strict Decimal MRR, ARR, Leakage Rate          |
|    - RulesEngine: Deterministic financial exception detection          |
|    - RiskEngine: Batch scan orchestrator with SHA-256 deduplication    |
|    - BillingProtectionEngine: Transactional period reservation locks   |
|    - PaymentMatcherEngine: Multi-signal weighted bank matcher          |
|    - ChurnScoring / MLModelPipeline: Scikit-learn LR vs Random Forest  |
|    - RecoveryExecutor: Safe automated vs approval-required actions     |
|    - AIProviderManager: Groq -> Gemini -> OpenRouter fallback chain    |
+------------------------------------------------------------------------+
                                   |
+------------------------------------------------------------------------+
| 4. ODOO ADAPTER & DATA ACCESS LAYER                                    |
|    - Standard Odoo ORM Models (sale.order, account.move, res.company)  |
|    - SubscriptIQ Custom Models (risk.case, billing.guard, audit.event) |
|    - Cryptographic SHA-256 Ledger (Append-only tamper-evident log)     |
|    - PostgreSQL Constraints & Composite Unique Indexes                 |
+------------------------------------------------------------------------+
```

---

## 3. Detailed Component Architecture

### 3.1 Continuous Revenue Guardian
- **Execution Mechanism:** Scheduled via native Odoo cron (`ir_cron_subscriptiq_guardian_scan`) every 15 minutes, with manual on-demand triggers via `subscriptiq.scan.wizard`.
- **Batch Processing:** Inspects records in batches of 500 without loading global datasets into memory.
- **Deduplication:** Computes an immutable SHA-256 fingerprint:
  $$\text{Fingerprint} = \text{SHA256}(\text{Company ID} : \text{Rule Code} : \text{Model} : \text{Record ID} : \text{Qualifier})$$
  Repeated scans update the existing case rather than generating alert noise.

### 3.2 Transactional Duplicate Billing Guard
- **The Problem:** Automated scheduled billing jobs or parallel employee invoice clicks can generate duplicate invoices for the same customer billing period.
- **The Solution:** A dedicated reservation model (`subscriptiq.billing.guard`) with a database-level unique constraint on `(company_id, subscription_id, period_start, period_end)`.
- **Atomic Execution Flow:**
  1. `acquire_billing_reservation`: Inserts a reservation lock with state `'reserved'` in the active database transaction. If another reservation exists, aborts with a user-facing exception.
  2. `validate_and_apply_discounts`: Verifies promotional rule date bounds and usage count.
  3. `create_invoice`: Generates the native `account.move`.
  4. `commit_billing_invoice`: Commits the invoice reference and marks the reservation `'invoiced'`.
  5. In case of error during invoice generation, the reservation is released (`'cancelled'`) to allow clean retry.

### 3.3 Smart Payment Reconciliation Engine
- **Deterministic Multi-Signal Scoring:**
  - Exact Invoice Reference Match: **+0.50**
  - Exact Amount Match: **+0.30**
  - Customer Identity Match: **+0.15**
  - Transaction Date Proximity ($\le 7$ days): **+0.05**
- **Confidence Tiers:**
  - $\ge 0.90$: High-Confidence Suggestion (eligible for 1-click reconciliation).
  - $0.70 - 0.89$: Manual Review Required.
  - $< 0.70$: Unmatched (flagged for accountant review).
- **Zero Fictitious Reconciliation:** Reconciliations always create an authentic `account.payment` record and execute native accounting allocation. The application never directly writes status fields like `payment_state = 'paid'`.

### 3.4 AI Copilot Free-Tier Architecture
- **Provider Priority:** Groq (developer free tier) $\to$ Google Gemini 2.0 Flash (free tier) $\to$ OpenRouter ($0/token free models) $\to$ Offline local fallback.
- **Security Whitelist:** The copilot cannot execute arbitrary SQL or Python code. It dispatches calls through a structured tool dispatcher (`CopilotToolRegistry`).
- **Two-Phase Write Operations:** Sensitive operations (e.g. reminders, quotes) create a proposal in `subscriptiq.action` awaiting human-in-the-loop authorization.

---

## 4. Scalability & Performance Strategy

1. **Pre-aggregated Risk Snapshots:** High-frequency dashboard views query lightweight `subscriptiq.risk.snapshot` records instead of recalculating 150,000 invoices on every page load.
2. **Indexed Foreign Keys & Composite Constraints:** Deterministic fingerprints and idempotency keys are indexed with B-Tree indexes.
3. **Strict Decimal Financial Arithmetic:** All revenue, tax, and discount computations use Python's `Decimal` with `ROUND_HALF_UP` to prevent floating-point drift.
4. **Resilience to Network Outages:** If AI providers experience rate-limiting (HTTP 429) or connectivity loss, the entire platform continues executing using deterministic rules and local ML.
