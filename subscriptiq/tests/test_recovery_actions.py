"""
SubscriptIQ Controlled Recovery Workflow Test Suite
Tests:
- Safe automated actions execute without approval
- Sensitive financial actions require dual authorization (awaiting_approval)
- Action approval execution workflow
- Idempotency key prevents duplicate action dispatch
"""

import unittest
from subscriptiq.services.odoo_adapter import Environment, UserError
from subscriptiq.services.recovery_executor import RecoveryExecutor, APPROVAL_REQUIRED_ACTIONS, SAFE_AUTOMATIC_ACTIONS

class TestRecoveryActions(unittest.TestCase):

    def setUp(self):
        self.env = Environment()

    def test_safe_automated_action_execution(self):
        """Safe automated reminder executes immediately."""
        action = RecoveryExecutor.propose_action(
            self.env,
            action_type='policy_customer_reminder',
            payload={'invoice_id': 1},
            user_id=1,
            company_id=1
        )
        self.assertEqual(action.state, 'completed')
        self.assertTrue(action.executed_at)

    def test_approval_required_action_workflow(self):
        """Sensitive actions like bulk_reminder or cancellation require manager authorization."""
        action = RecoveryExecutor.propose_action(
            self.env,
            action_type='cancel_subscription',
            payload={'subscription_id': 10},
            user_id=1,
            company_id=1
        )
        self.assertEqual(action.state, 'awaiting_approval')

        # Manager approves action
        res = RecoveryExecutor.approve_action(self.env, action, approver_id=1)
        self.assertTrue(res['success'])
        self.assertEqual(action.state, 'completed')
        self.assertEqual(action.approved_by, 1)

    def test_idempotent_action_dispatch(self):
        """Re-proposing the exact same action returns existing action and prevents duplicate execution."""
        act1 = RecoveryExecutor.propose_action(
            self.env,
            action_type='approve_renewal_offer',
            payload={'subscription_id': 42},
            user_id=1,
            company_id=1
        )

        act2 = RecoveryExecutor.propose_action(
            self.env,
            action_type='approve_renewal_offer',
            payload={'subscription_id': 42},
            user_id=1,
            company_id=1
        )

        self.assertEqual(act1.id, act2.id)
        self.assertEqual(act1.idempotency_key, act2.idempotency_key)

if __name__ == '__main__':
    unittest.main()
