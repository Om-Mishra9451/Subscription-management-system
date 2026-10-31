#!/usr/bin/env python3
"""
SubscriptIQ Automated Test Runner
Executes complete automated test suites across:
- Security & Authentication
- Subscription & Product Extensions
- Transactional Billing Guards
- Payment Reconciliation & Deterministic Matching
- Revenue Guardian Risk Engine & Deduplication
- Controlled Recovery Workflows & Idempotency
- Revenue Dashboard & Precision Arithmetic
- AI Copilot Fallback & Whitelist Tools
- Multi-Company Data Isolation
"""

import sys
import unittest
import os

# Ensure current directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import subscriptiq.models

def run_all_tests():
    print("=" * 80)
    print("  SUBSCRIPTIQ AUTOMATED TEST SUITE EXECUTION")
    print("  Autonomous Revenue Assurance Engine for Odoo")
    print("=" * 80)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_modules = [
        'subscriptiq.tests.test_security',
        'subscriptiq.tests.test_subscription_adapter',
        'subscriptiq.tests.test_billing_guard',
        'subscriptiq.tests.test_payment_matcher',
        'subscriptiq.tests.test_risk_engine',
        'subscriptiq.tests.test_recovery_actions',
        'subscriptiq.tests.test_dashboard',
        'subscriptiq.tests.test_copilot',
        'subscriptiq.tests.test_multi_company'
    ]

    for mod_name in test_modules:
        try:
            mod_suite = loader.loadTestsFromName(mod_name)
            suite.addTests(mod_suite)
            print(f"  [LOADED] {mod_name}")
        except Exception as e:
            print(f"  [ERROR LOADING] {mod_name}: {e}")

    print("-" * 80)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 80)
    print(f"  TEST SUMMARY: {result.testsRun} tests run")
    print(f"  Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    print("=" * 80)

    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(run_all_tests())
