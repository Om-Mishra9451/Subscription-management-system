# SubscriptIQ — Environment Setup & Configuration

This guide explains how to configure your local or server environment for **SubscriptIQ**, including Python virtual environments and free-tier AI API configuration.

---

## 1. Python Environment Setup

We recommend using Python 3.10+ in a dedicated virtual environment.

```bash
# Navigate to the project root
cd "/Users/eklavya/Documents/Subscription Management System"

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS / Linux:
source venv/bin/activate
# On Windows (cmd):
# venv\Scripts\activate.bat
# On Windows (PowerShell):
# .\venv\Scripts\Activate.ps1

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r subscriptiq/requirements.txt
```

---

## 2. Configuration (`.env`)

SubscriptIQ uses standard environment variables to manage provider keys and operational parameters. An initial template is provided in `.env.example`.

### Create your `.env` file:
```bash
cp .env.example .env
```

### Environment Variable Reference

```ini
# ==============================================================================
# SubscriptIQ — Production Environment Configuration
# ==============================================================================

# Core System Settings
ODOO_ENVIRONMENT=production
SUBSCRIPTIQ_LOG_LEVEL=INFO
DEFAULT_AI_PROVIDER=groq

# ------------------------------------------------------------------------------
# Free-Tier AI Providers (Zero Paid Cloud Dependencies)
# ------------------------------------------------------------------------------

# 1. Groq Free Tier (Default Provider - High Speed LLaMA 3.3)
# Sign up at: https://console.groq.com/keys
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# 2. Google Gemini Free Tier (Secondary Fallback)
# Sign up at: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=AIzaSy_your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# 3. OpenRouter Free Tier (Tertiary Fallback)
# Sign up at: https://openrouter.ai/keys
OPENROUTER_API_KEY=sk-or-v1-your_openrouter_key_here
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free

# ------------------------------------------------------------------------------
# Revenue Guardian Engine Parameters
# ------------------------------------------------------------------------------
GUARDIAN_DEFAULT_SCAN_INTERVAL=hourly
AUTO_APPROVAL_THRESHOLD=500.00
DUAL_AUTHORIZATION_THRESHOLD=5000.00
DUNNING_GRACE_PERIOD_DAYS=7
```

---

## 3. Obtaining Free-Tier AI Keys (Zero Cost)

SubscriptIQ is explicitly engineered to operate on **100% free-tier services**. It will never require credit cards or paid cloud billing.

### 1. Groq (Primary Provider — Ultra Low Latency)
1. Visit [https://console.groq.com](https://console.groq.com).
2. Sign in with GitHub or Google.
3. Navigate to **API Keys** and click **Create API Key**.
4. Copy the generated key (`gsk_...`) into `GROQ_API_KEY` in `.env`.

### 2. Google Gemini (Secondary Provider — High Context)
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Sign in with your Google account.
3. Click **Create API Key** in a new or existing project.
4. Copy the generated key (`AIzaSy...`) into `GEMINI_API_KEY` in `.env`.

### 3. OpenRouter (Tertiary Provider — Free Open Models)
1. Visit [OpenRouter Keys](https://openrouter.ai/keys).
2. Sign in and generate an API key.
3. Copy the key (`sk-or-v1-...`) into `OPENROUTER_API_KEY` in `.env`.

> [!NOTE]
> **Complete Offline Fallback**: If no API keys are provided or if external networks are unreachable, SubscriptIQ's `AIProviderManager` will automatically fall back to its internal deterministic rules synthesizer without raising unhandled exceptions.

---

## 4. Verification

Run the test suite to confirm your environment is operational:

```bash
python3 run_tests.py
```
If you see `30/30 tests PASSED`, your environment is fully configured and ready.
