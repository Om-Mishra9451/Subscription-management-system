"""
SubscriptIQ Scan Wizard
Provides an interactive on-demand scanning wizard for Revenue Guardian.
"""

from ..services.odoo_adapter import models, fields, api
from ..services.risk_engine import RiskEngine

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
