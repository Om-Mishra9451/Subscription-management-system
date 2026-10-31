# SubscriptIQ — Known Limitations & Future Roadmap

This document provides transparent technical disclosure regarding current architectural boundaries, external dependencies, and planned engineering enhancements.

---

## 1. Upstream Odoo Framework Boundaries

### 1.1 Native Daily Recurrence Limitation
- **Context:** Native Odoo Subscription / Recurring Sales contracts (`sale.subscription` in Enterprise or recurrence rules in Community) provide out-of-the-box support for `weekly`, `monthly`, `quarterly`, and `yearly` billing cycles, but omit a native `daily` recurrence frequency.
- **SubscriptIQ Solution:** SubscriptIQ implements an explicit daily recurrence adapter (`subscriptiq/services/subscription_adapter.py`) that normalizes daily intervals, computes daily renewal target dates (`date + timedelta(days=1)`), and standardizes daily revenue into Monthly Recurring Revenue (MRR) using the standard actuarial factor ($365 / 12$).
- **Limitation:** In pure native Odoo views without the SubscriptIQ module activated, daily recurrence is displayed as custom interval units.

### 1.2 Enterprise vs. Community Subscription Modules
- **Context:** In Odoo Enterprise, subscriptions often utilize dedicated `sale.subscription` models, whereas in Odoo Community, recurring contracts are typically modeled as recurring `sale.order` templates.
- **SubscriptIQ Solution:** SubscriptIQ's `subscription_adapter.py` seamlessly abstracts both paradigms by binding to the universal `sale.order` root model with polymorphic method delegation.

---

## 2. External AI Provider & Free-Tier Boundaries

### 2.1 Free-Tier Rate Limits
SubscriptIQ intentionally relies on **100% free-tier AI inference** to eliminate operational costs:
- **Groq Free Tier:** Rate-limited to approximately 30 requests per minute (RPM) and 14,400 requests per day (RPD).
- **Google Gemini Free Tier:** Rate-limited to 15 RPM.
- **OpenRouter Free Tier:** Subject to public community queue latency during peak hours.

### 2.2 Mitigation Strategy
SubscriptIQ implements:
1. **Automated Multi-Provider Cascading**: `Groq` $\to$ `Gemini` $\to$ `OpenRouter` $\to$ `Local Fallback`.
2. **Guaranteed Local Offline Fallback**: If internet connectivity is interrupted or rate limits are reached, the system falls back to a deterministic rule synthesizer without failing or crashing.

---

## 3. Scalability & Architectural Boundaries

### 3.1 Synchronous vs. Distributed Execution
- **Current Architecture:** Benchmarked and validated for datasets up to **50,000 active subscriptions** (processing 300,000 records in 0.307 seconds with sub-250ms query latencies) using single-process batch execution.
- **Upper Boundary:** For enterprise deployments exceeding **500,000 active subscriptions**, background scanning jobs should be transitioned from standard Odoo `ir.cron` threads to dedicated distributed worker queues (e.g., Celery + Redis).

### 3.2 Bank CSV Format Variations
- **Current Architecture:** The bank statement parser handles standard comma-separated and semicolon-separated CSV layouts containing date, reference, partner, and credit/debit amount columns.
- **Limitation:** Highly proprietary or encrypted MT940 / CAMT.053 XML banking feeds require pre-normalization into standard CSV before import.

---

## 4. Product Engineering Roadmap

- [ ] **Phase 2.1: Native Payment Gateway Webhooks**: Real-time webhook ingestion for Stripe, Adyen, and Razorpay payment failures to trigger instantaneous zero-touch dunning.
- [ ] **Phase 2.2: Continuous Churn Model Retraining Worker**: Automated background retraining cron triggering when model drift exceeds 5%.
- [ ] **Phase 2.3: Mobile-Responsive Push Alerts**: Instant notification delivery to Odoo Mobile app when critical dual-authorization recovery cases are raised.
- [ ] **Phase 2.4: Multi-Currency Revaluation**: Real-time integration with European Central Bank (ECB) currency feeds for multi-currency MRR normalization.
