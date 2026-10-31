"""
SubscriptIQ Recovery Action Model
Tracks lifecycle, approval workflow, and execution results for automated and human-approved recovery operations.
"""

from ..services.odoo_adapter import models, fields, api

class SubscriptiqAction(models.Model):
    _name = 'subscriptiq.action'
    _description = 'Recovery Workflow Action'
    _order = 'create_date desc'

    name = fields.Char(string="Action Summary", required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company or 1, required=True)
    risk_case_ids = fields.Many2many('subscriptiq.risk.case', string="Associated Risk Cases")

    action_type = fields.Selection([
        ('policy_customer_reminder', 'Automated Customer Reminder'),
        ('renewal_expiry_notice', 'Renewal Expiration Notice'),
        ('bulk_reminder_campaign', 'Bulk Payment Reminder Campaign'),
        ('approve_renewal_offer', 'Draft Renewal Offer Approval'),
        ('modify_subscription_plan', 'Subscription Plan Change'),
        ('execute_payment_reconciliation', 'Bank Payment Reconciliation'),
        ('issue_refund', 'Customer Refund Request'),
        ('invoice_write_off', 'Debt Write-Off Authorization'),
        ('cancel_subscription', 'Subscription Cancellation')
    ], string="Action Type", required=True)

    state = fields.Selection([
        ('proposed', 'Proposed'),
        ('awaiting_approval', 'Awaiting Manager Approval'),
        ('approved', 'Approved for Execution'),
        ('executing', 'Executing'),
        ('completed', 'Completed Successfully'),
        ('failed', 'Execution Failed'),
        ('rejected', 'Rejected by Manager')
    ], string="Status", default='proposed', required=True)

    requested_by = fields.Many2one('res.users', string="Initiating User", default=lambda self: self.env.uid)
    approved_by = fields.Many2one('res.users', string="Authorizing Manager")
    approved_at = fields.Datetime(string="Approval Timestamp")
    executed_at = fields.Datetime(string="Execution Timestamp")

    idempotency_key = fields.Char(string="Idempotency Key", index=True, copy=False)
    request_payload = fields.Text(string="Request Parameters Payload")
    result = fields.Text(string="Execution Result Summary")
    error_message = fields.Text(string="Error Details")

    def action_approve(self):
        """Authorizes and executes an action awaiting approval."""
        from ..services.recovery_executor import RecoveryExecutor
        for act in self:
            RecoveryExecutor.approve_action(self.env, act, approver_id=self.env.uid)
        return True

    def action_reject(self, reason="Rejected by manager"):
        """Rejects the action."""
        from ..services.recovery_executor import RecoveryExecutor
        for act in self:
            RecoveryExecutor.reject_action(self.env, act, rejector_id=self.env.uid, reason=reason)
        return True
