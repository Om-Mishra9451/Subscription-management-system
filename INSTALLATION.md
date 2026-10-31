# SubscriptIQ — Installation & Deployment Guide

This guide details how to install and activate **SubscriptIQ** within standard Odoo 19.0 / 20.0 environments, as well as how to run the standalone assurance engine.

---

## 1. Prerequisites

### System Requirements
- **Python**: 3.10, 3.11, or 3.12
- **PostgreSQL**: Version 14, 15, or 16
- **Odoo Editions**: Community or Enterprise (Version 19.0 or 20.0)

### Native Odoo Dependencies
SubscriptIQ leverages native Odoo modules without duplicating existing accounting or subscription tables:
- `base` (Core Odoo framework)
- `sale` (Sales orders, quotations, product variants)
- `account` (Invoicing, payments, reconciliation, fiscal positions)
- `mail` (Chatter, audit messaging, dunning notifications)

---

## 2. Standard Odoo Addon Installation

### Step 1: Clone / Place Addon Directory
Ensure the `subscriptiq` folder is located within your Odoo custom addons directory:

```bash
cd /opt/odoo/custom-addons
git clone <repository_url> .
# Verify the subscriptiq directory exists:
ls -la /opt/odoo/custom-addons/subscriptiq
```

### Step 2: Configure `odoo.conf`
Edit your Odoo server configuration file (e.g., `/etc/odoo/odoo.conf` or `~/.odoo/odoo.conf`):

```ini
[options]
addons_path = /opt/odoo/odoo/addons,/opt/odoo/custom-addons
admin_passwd = your_master_password
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo_secure_password
```

### Step 3: Install Required Python Dependencies
Install the required packages in your Odoo virtual environment:

```bash
pip install -r subscriptiq/requirements.txt
```
*(Dependencies: `scikit-learn>=1.3.0`, `requests>=2.31.0`)*

### Step 4: Update Addons List and Install Module

#### Method A: Via Odoo Web Client (Recommended)
1. Log in to Odoo as an Administrator.
2. Enable Developer Mode (**Settings** $\to$ **Developer Tools** $\to$ **Activate the developer mode**).
3. Navigate to **Apps** $\to$ **Update Apps List** and confirm.
4. Search for `SubscriptIQ` in the Apps search bar (remove the `Apps` filter if necessary).
5. Click **Activate** (Install).

#### Method B: Via Command Line CLI
Execute the installation directly using the Odoo CLI runner:

```bash
python3 odoo-bin -c /etc/odoo/odoo.conf -d brightloop_db -i subscriptiq --stop-after-init
```

---

## 3. Initial Module Activation Checklist

Once installed, SubscriptIQ will automatically:
1. Seed default deterministic rules in `subscriptiq.rule` (`OVERDUE_INVOICE`, `EXPIRING_SUBSCRIPTION`, `EXPIRED_DISCOUNT`, `UNMATCHED_PAYMENT`, `FAILED_PAYMENT`).
2. Initialize multi-company system sequences (`SCAN-...`, `RISK-...`, `ACT-...`).
3. Set up the automated scheduled action `SubscriptIQ: Continuous Revenue Guardian Scanner` (hourly default).
4. Populate initial email notification templates in `mail.template`.

---

## 4. Standalone Mode (Headless Testing & Benchmarking)

SubscriptIQ includes an internal compatibility adapter (`subscriptiq/services/odoo_adapter.py`) allowing full headless execution, automated testing, and high-scale benchmarks without needing a running Odoo web server.

### Run Unit & Integration Tests:
```bash
python3 run_tests.py
```
*Expected: 30/30 tests PASSED with 0 errors.*

### Run 50,000-Subscription Scalability Benchmark:
```bash
python3 run_benchmark.py
```
*Validates database indexing, memory isolation, and p95 latency under 2.0 seconds.*

### Run End-to-End Judge Demonstration:
```bash
python3 demo_runner.py
```
*Executes all 6 interactive revenue assurance scenarios.*
