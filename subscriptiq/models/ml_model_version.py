"""
SubscriptIQ ML Model Version Model
Tracks model training runs, metrics (ROC-AUC, Precision, Recall, Brier), and active champion model.
"""

from ..services.odoo_adapter import models, fields

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
