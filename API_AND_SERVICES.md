# SubscriptIQ — API & Services Architecture

SubscriptIQ provides modular, decoupled Python services implementing core business logic independently of HTTP controllers. Each service accepts and yields standard Python structures, guaranteeing clean testability, transaction boundaries, and headless operational execution.

---

## 1. Service Layer Overview

```
                      +-----------------------------+
                      |   Odoo UI / Controllers     |
                      |  /subscriptiq/copilot/ask   |
                      +--------------+--------------+
                                     |
               +---------------------+---------------------+
               |                     |                     |
               v                     v                     v
     +-------------------+ +-------------------+ +-------------------+
     |   Risk Engine     | | Billing Protection| |  Payment Matcher  |
     | (Guardian Scans)  | |  (Idempotency)    | |  (Weighted Rec)   |
     +---------+---------+ +---------+---------+ +---------+---------+
               |                     |                     |
               +---------------------+---------------------+
                                     |
                                     v
                       +---------------------------+
                       |    Revenue Calculator     |
                       | (Strict Decimal Metrics)  |
                       +-------------+-------------+
                                     |
                                     v
                       +---------------------------+
                       |    AI Provider Manager    |
                       |  (Groq/Gemini/OpenRouter) |
                       +---------------------------+
```

---

## 2. Core Service Interfaces

### 2.1 `RevenueCalculator` (`services/revenue_calculator.py`)
Computes auditable financial metrics with zero floating-point drift using Python's `decimal.Decimal`.

#### Class Definition
```python
class RevenueCalculator:
    @staticmethod
    def normalize_to_mrr(amount: Union[Decimal, float], recurrence: str) -> Decimal:
        """
        Normalizes any billing interval into standard Monthly Recurring Revenue (MRR).
        Supported recurrence strings: 'daily', 'weekly', 'monthly', 'quarterly', 'yearly'
        Conversion formulas:
          - daily: amount * (365 / 12)
          - weekly: amount * (52 / 12)
          - monthly: amount
          - quarterly: amount / 3
          - yearly: amount / 12
        """

    @staticmethod
    def calculate_arr(mrr: Decimal) -> Decimal:
        """Computes Annual Recurring Revenue (ARR = MRR * 12)."""

    @staticmethod
    def compute_dashboard_metrics(env, company_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Aggregates company-scoped KPIs:
          - total_active_subscriptions (int)
          - mrr (float, 2 decimals)
          - arr (float, 2 decimals)
          - revenue_collected (float)
          - outstanding_amount (float)
          - overdue_invoices_count (int)
          - overdue_amount (float)
          - revenue_at_risk (float)
          - verified_recovered_revenue (float)
          - revenue_leakage_rate (float percentage)
        """
```

---

### 2.2 `RulesEngine` (`services/rules_engine.py`)
Deterministic rules evaluator evaluating individual records against risk policies.

#### Standard Rule Evaluation
```python
class RulesEngine:
    @classmethod
    def evaluate_rule(cls, rule_code: str, record: Any, env: Any) -> Optional[Dict[str, Any]]:
        """
        Evaluates a single target record against a registered rule code.
        Returns None if healthy, or a RiskPayload dictionary if an anomaly is detected.
        
        RiskPayload structure:
          {
              'rule_code': str,
              'severity': 'low' | 'medium' | 'high' | 'critical',
              'amount_at_risk': Decimal,
              'recommended_action': str,
              'evidence': dict,
              'partner_id': int,
              'subscription_id': Optional[int],
              'invoice_id': Optional[int],
              'fingerprint': str (SHA-256)
          }
        """

    @staticmethod
    def generate_fingerprint(rule_code: str, record_type: str, record_id: int, discriminant: str) -> str:
        """Generates deterministic SHA-256 hash preventing duplicate case creation."""
```

#### Implemented Core Rules:
1. `OVERDUE_INVOICE`: Triggers when `state == 'posted'`, `amount_residual > 0`, and `invoice_date_due < today`. Severity scales from `medium` (1–14 days) to `critical` (>30 days).
2. `EXPIRING_SUBSCRIPTION`: Triggers when `subscriptiq_status == 'active'` and `next_renewal_date <= today + 7 days`.
3. `EXPIRED_DISCOUNT`: Triggers if an invoice line references an expired coupon or exceeded usage counter.
4. `UNMATCHED_PAYMENT`: Triggers on raw imported bank statement lines lingering unmatched $> 48$ hours.
5. `FAILED_PAYMENT`: Triggers on repeated payment gateway transaction failures ($\ge 2$).

---

### 2.3 `RiskEngine` (`services/risk_engine.py`)
Coordinates batch scanning across tenants, deduplication, and anomaly case state transitions.

```python
class RiskEngine:
    @classmethod
    def run_guardian_scan(cls, env, company_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Executes a continuous guardian scan:
          1. Queries active subscriptions, posted unpaid invoices, and unmatched payments.
          2. Runs deterministic rule evaluation.
          3. Upserts `subscriptiq.risk.case` records using the fingerprint unique constraint.
          4. Emits chained `subscriptiq.audit.event` records.
          5. Creates a completed `subscriptiq.scan` telemetry run.
        Returns:
          {
              'scan_id': int,
              'records_scanned': int,
              'cases_created': int,
              'cases_updated': int,
              'revenue_at_risk': float,
              'duration_ms': float
          }
        """
```

---

### 2.4 `BillingProtectionEngine` (`services/billing_protection.py`)
Transactional concurrency guard guaranteeing invoice idempotency and discount validity prior to accounting writes.

```python
class BillingProtectionEngine:
    @classmethod
    def reserve_billing_slot(cls, env, subscription_id: int, period_start: date, period_end: date) -> str:
        """
        Acquires an atomic billing reservation lock.
        Raises `DuplicateBillingError` if a reservation or invoice already exists
        for the given (company_id, subscription_id, period_start, period_end) tuple.
        Returns: idempotency_key (str)
        """

    @classmethod
    def commit_billing_slot(cls, env, idempotency_key: str, invoice_id: int) -> None:
        """Transitions reservation to 'committed' and associates the newly generated invoice."""

    @classmethod
    def validate_discounts_pre_billing(cls, env, subscription_id: int, invoice_date: date) -> List[Dict[str, Any]]:
        """
        Audits all discounts applied to the subscription.
        Rejects any line items whose discounts expired or exceeded max usage counters.
        """
```

---

### 2.5 `PaymentMatcherEngine` (`services/payment_matcher.py`)
Multi-factor deterministic bank statement reconciliation engine.

```python
class PaymentMatcherEngine:
    WEIGHT_REFERENCE = 0.50
    WEIGHT_PARTNER = 0.30
    WEIGHT_AMOUNT = 0.15
    WEIGHT_DATE = 0.05
    AUTO_RECONCILE_THRESHOLD = 0.85

    @classmethod
    def process_import_lines(cls, env, import_id: int) -> Dict[str, Any]:
        """
        Evaluates unallocated statement lines against open receivables:
          1. Calculates composite confidence score (0.00 - 1.00).
          2. Auto-reconciles pairs scoring >= 0.85 within auto-approval limits.
          3. Creates `subscriptiq.match.candidate` records for lower-confidence pairs.
          4. Updates invoice `subscriptiq_risk_state` and records Verified Recovered Revenue.
        """
```

---

### 2.6 `AIProviderManager` & Copilot Interface (`services/ai/`)
Pluggable LLM abstraction utilizing free-tier providers with zero paid cloud dependencies.

```python
class AIProviderManager:
    """
    Priority Routing Chain:
      1. Groq (llama-3.3-70b-versatile) - Ultra-fast free tier
      2. Google Gemini (gemini-1.5-flash) - Generous free tier
      3. OpenRouter (meta-llama/llama-3.3-70b-instruct:free) - Community free tier
      4. Local Deterministic Rule Engine - Guaranteed offline zero-downtime fallback
    """

    def generate_chat_response(self, user_query: str, session_context: Optional[dict] = None) -> str:
        """
        1. Sanitize prompt against injection and jailbreak payloads.
        2. Detect if an whitelisted tool is required (e.g. get_kpis, inspect_case).
        3. Dispatch request to available free-tier provider.
        4. Fallback gracefully to offline rule synthesis if internet/API keys unavailable.
        """
```

---

## 3. HTTP Endpoints

### `POST /subscriptiq/copilot/ask`
Interactive natural-language endpoint consumed by the Enterprise OWL / JS UI widget.

#### Request Payload
```json
{
  "prompt": "What is our current revenue at risk and what caused it?",
  "company_id": 1
}
```

#### Response Payload
```json
{
  "status": "success",
  "provider": "Groq (llama-3.3-70b-versatile)",
  "response": "Currently, Brightloop Software has $8,450.00 at risk across 3 open cases. The largest exposure is Case RISK-2026-0001 ($5,000.00) due to Invoice INV/2026/0004 being 18 days overdue.",
  "suggested_actions": [
    {
      "label": "Execute Dunning Notice",
      "action": "execute_dunning",
      "params": {"case_id": 1}
    }
  ],
  "requires_approval": false
}
```
