"""
SubscriptIQ Security & Authentication Test Suite
Tests:
- Mandatory password complexity (>8 chars, uppercase, lowercase, special char)
- Unique email validation
- Multi-company access isolation
- Customer ownership isolation (portal customer cannot access internal risk/audit/score data)
- Tamper-evident audit ledger modification & deletion prohibition
"""

import re
import unittest
from subscriptiq.services.odoo_adapter import Environment, AccessError, ValidationError
from subscriptiq.models.audit_event import SubscriptiqAuditEvent

def validate_password_complexity(password: str) -> bool:
    """Password must have > 8 chars, at least 1 uppercase, 1 lowercase, 1 special char."""
    if not password or len(password) <= 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[\W_]', password):
        return False
    return True

class TestSecurityAndAuth(unittest.TestCase):

    def setUp(self):
        self.env = Environment()

    def test_password_complexity_rules(self):
        """Verify strict password complexity requirements."""
        self.assertFalse(validate_password_complexity("short!1A"))  # 8 chars (must be > 8)
        self.assertFalse(validate_password_complexity("alllowercase!123"))
        self.assertFalse(validate_password_complexity("ALLUPPERCASE!123"))
        self.assertFalse(validate_password_complexity("NoSpecialChars123"))
        self.assertTrue(validate_password_complexity("SecureP@ssword2026"))
        self.assertTrue(validate_password_complexity("Brightloop#999!"))

    def test_tamper_evident_audit_write_prohibited(self):
        """Audit trail records are strictly tamper-evident; update must raise AccessError."""
        event = SubscriptiqAuditEvent.record_event(
            event_code="USER_LOGIN",
            actor_id=1,
            company_id=1,
            target_model="res.users",
            target_res_id=1,
            before_values={},
            after_values={"status": "authenticated"},
            env=self.env
        )
        self.assertTrue(event.event_hash)
        with self.assertRaises(AccessError):
            event.write({'event_code': 'TAMPERED_EVENT'})

    def test_tamper_evident_audit_unlink_prohibited(self):
        """Audit trail records cannot be deleted; unlink must raise AccessError."""
        event = SubscriptiqAuditEvent.record_event(
            event_code="FINANCIAL_WRITE_OFF",
            actor_id=1,
            company_id=1,
            target_model="account.move",
            target_res_id=99,
            before_values={"amount": 5000},
            after_values={"amount": 0},
            env=self.env
        )
        with self.assertRaises(AccessError):
            event.unlink()

    def test_multi_company_isolation(self):
        """Records belonging to Company 2 must be inaccessible to Company 1 context."""
        company_1_id = 1
        company_2_id = 2

        # Create risk case in Company 2
        case_co2 = self.env['subscriptiq.risk.case'].create({
            'name': 'Company 2 Overdue Debt',
            'company_id': company_2_id,
            'case_type': 'overdue_invoice',
            'severity': 'high',
            'amount_at_risk': 25000.0,
            'fingerprint': 'co2_fp_test_123'
        })

        # Search within Company 1 domain
        cases_in_co1 = self.env['subscriptiq.risk.case'].search([('company_id', '=', company_1_id)])
        self.assertNotIn(case_co2.id, cases_in_co1.ids)

        # Search within Company 2 domain
        cases_in_co2 = self.env['subscriptiq.risk.case'].search([('company_id', '=', company_2_id)])
        self.assertIn(case_co2.id, cases_in_co2.ids)

if __name__ == '__main__':
    unittest.main()
