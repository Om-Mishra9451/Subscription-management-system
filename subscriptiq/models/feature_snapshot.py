"""
SubscriptIQ Machine Learning and Audit Logging Supporting Models
Handles historical feature vectors, ML champion model versions, and Copilot query audit logs.
"""

from ..services.odoo_adapter import models, fields

class SubscriptiqFeatureSnapshot(models.Model):
    _name = 'subscriptiq.feature.snapshot'
    _description = 'Customer Feature Snapshot for ML'
    _order = 'snapshot_date desc'

    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company or 1)
    snapshot_date = fields.Date(string="Snapshot Date", required=True)

    features_json = fields.Text(string="Extracted Features Vector (JSON)")
    churn_label = fields.Integer(string="Outcome Churn Label (0=Retained, 1=Churned)", default=0)

class SubscriptiqMLModelVersion(models.Model):
    _name = 'subscriptiq.ml.model.version'
    _description = 'ML Churn Model Version'
    _order = 'trained_at desc'

    version = fields.Char(string="Model Version Identifier", required=True)
    model_type = fields.Selection([
        ('logistic_regression', 'Baseline Logistic Regression'),
        ('random_forest', 'Challenger Random Forest'),
        ('rules_fallback', 'Deterministic Rules Fallback')
    ], string="Model Architecture", required=True, default='logistic_regression')

    roc_auc = fields.Float(string="ROC-AUC Score")
    precision = fields.Float(string="Precision Score")
    recall = fields.Float(string="Recall Score")
    brier_score = fields.Float(string="Brier Calibration Score")

    dataset_size = fields.Integer(string="Training Dataset Size")
    activated = fields.Boolean(string="Production Active Model", default=False)
    trained_at = fields.Datetime(string="Training Timestamp", default=lambda self: fields.Datetime.now())
    notes = fields.Text(string="Model Notes & Hyperparameters")

class SubscriptiqCopilotLog(models.Model):
    _name = 'subscriptiq.copilot.log'
    _description = 'AI Copilot Audit Query Log'
    _order = 'timestamp desc'

    user_id = fields.Many2one('res.users', string="User", required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company or 1)
    query = fields.Text(string="Sanitized User Query", required=True)
    response = fields.Text(string="AI Grounded Response")
    provider = fields.Char(string="AI Provider Used")
    model = fields.Char(string="Model Identifier")
    tool_calls = fields.Text(string="Tool Calls Executed (JSON)")
    timestamp = fields.Datetime(string="Timestamp", default=lambda self: fields.Datetime.now())
