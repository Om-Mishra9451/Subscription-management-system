#!/usr/bin/env python3
"""
SubscriptIQ Database Inspector CLI
Allows inspecting all tables and records directly from the command line.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subscriptiq.services.odoo_adapter import Environment
from subscriptiq.services.revenue_calculator import RevenueCalculator

def inspect_all():
    env = Environment()
    
    print("\n" + "=" * 80)
    print("  SUBSCRIPTIQ DATABASE INSPECTOR — ALL TABLES & RECORDS")
    print("=" * 80)
    
    # Query web server state if running, else local state
    import urllib.request
    import json
    
    try:
        req = urllib.request.urlopen("http://localhost:8069/api/state", timeout=2)
        data = json.loads(req.read().decode('utf-8'))
        print("\n[Connected to Live Server on http://localhost:8069]")
        
        print("\n--- 1. REVENUE ASSURANCE METRICS ---")
        for k, v in data.get('metrics', {}).items():
            if k != 'risk_breakdown':
                print(f"  • {k:28}: {v}")

        print(f"\n--- 2. TABLE: subscriptiq_risk_case ({len(data.get('cases', []))} records) ---")
        for c in data.get('cases', []):
            print(f"  [{c['name']}] | Customer: {c['partner_name']} | Severity: {c['severity'].upper()} | Amount: ${c['amount_at_risk']:,.2f} | Status: {c['state']}")
            print(f"    Action: {c['recommended_action']}")

        print(f"\n--- 3. TABLE: subscriptiq_audit_event ({len(data.get('audit_events', []))} records) ---")
        for ev in data.get('audit_events', []):
            print(f"  [Seq #{ev['sequence']}] {ev['timestamp']} | Event: {ev['event_type']:22} | Hash: {ev['current_hash'][:20]}...")

    except Exception:
        print("\n[Server not running. Run 'python3 demo_runner.py' or 'python3 web_server.py 8069']")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    inspect_all()
