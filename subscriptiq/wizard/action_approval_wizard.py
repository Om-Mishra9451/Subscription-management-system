"""
SubscriptIQ Action Approval & Scan Wizards
Provides interactive dialogs for dual authorization of financial operations and on-demand guardian scans.
"""

from ..services.odoo_adapter import models, fields, api, UserError
from ..services.recovery_executor import RecoveryExecutor
from ..services.risk_engine import RiskEngine

class ActionApprovalWizard(models.TransientModel):
    _name = 'subscriptiq.action.approval.wizard'
    _description = 'Recovery Action Approval Wizard'

    action_id = fields.Many2one('subscriptiq.action', string="Recovery Action", required=True)
    decision = fields.Selection([
        ('approve', 'Approve and Execute Immediately'),
        ('reject', 'Reject Proposal')
    ], string="Decision", default='approve', required=True)
    notes = fields.Text(string="Authorization Notes / Rejection Reason")

    def action_confirm_decision(self):
        """Processes manager decision."""
        self.ensure_one()
        act = self.action_id
        if self.decision == 'approve':
            RecoveryExecutor.approve_action(self.env, act, approver_id=self.env.uid)
        else:
            RecoveryExecutor.reject_action(self.env, act, rejector_id=self.env.uid, reason=self.notes or "Rejected in approval wizard")
        return {'type': 'ir.actions.act_window_close'}

class ScanWizard(models.TransientModel):
    _name = 'subscriptiq.scan.wizard'
    _description = 'On-Demand Revenue Guardian Scan Wizard'

    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company or 1, required=True)
    scan_scope = fields.Selection([
        ('all', 'Full Enterprise Scan (All Rules)'),
        ('overdue', 'Overdue Invoices Only'),
        ('expiring', 'Upcoming Expirations Only'),
        ('payments', 'Unmatched Payments & Failed Transactions')
    ], string="Scan Scope", default='all', required=True)

    def action_run_scan(self):
        """Launches guardian scan."""
        self.ensure_one()
        scan_record = self.env['subscriptiq.scan'].create({
            'name': f"Manual Scan ({self.scan_scope}) - {fields.Datetime.now()}",
            'company_id': self.company_id.id,
            'state': 'in_progress'
        })
        RiskEngine.execute_guardian_scan(self.env, company_id=self.company_id.id, scan_record=scan_record)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Scan Result',
            'res_model': 'subscriptiq.scan',
            'res_id': scan_record.id,
            'view_mode': 'form',
            'target': 'current'
        }
