"""
SubscriptIQ Customer Risk Intelligence & Machine Learning Pipeline
Combines deterministic, fully explainable rules-based risk scoring with a local Scikit-Learn
predictive churn engine (Logistic Regression baseline vs Random Forest Classifier).
Includes chronological splits, ROC-AUC, Precision, Recall, and Brier calibration evaluation.
"""

import datetime
import logging
from decimal import Decimal

_logger = logging.getLogger(__name__)

# Try importing scikit-learn
try:
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import roc_auc_score, precision_score, recall_score, brier_score_loss
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    _logger.warning("Scikit-Learn not found in environment; operating in deterministic rules mode.")

class CustomerRiskScorer:
    """Computes explainable deterministic risk prioritization scores."""

    @classmethod
    def calculate_deterministic_score(cls, env, partner_id, company_id=None):
        """
        Calculates explainable risk score (0-100) using deterministic business signals:
        - Invoice overdue 1-7 days: +15 (mutually exclusive)
        - Invoice overdue 8-30 days: +25
        - Invoice overdue > 30 days: +35
        - Failed payments in last 30 days: +20
        - Renewal due within 7 days: +15
        - Unmatched transaction older than 7 days: +15
        Cap at 100.
        """
        score = 0
        factors = []
        today = datetime.date.today()
        cid = company_id or 1

        # 1. Invoice overdue signals (Mutually exclusive maximum overdue range)
        inv_domain = [
            ('partner_id', '=', partner_id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('amount_residual', '>', 0.0)
        ]
        if company_id:
            inv_domain.append(('company_id', '=', company_id))

        invoices = env['account.move'].search(inv_domain) if 'account.move' in env else []
        max_overdue_days = 0
        total_residual = 0.0

        for inv in invoices:
            total_residual += float(getattr(inv, 'amount_residual', 0.0))
            due_date = getattr(inv, 'invoice_date_due', None)
            if due_date:
                due_d = datetime.date.fromisoformat(str(due_date)[:10])
                days = (today - due_d).days
                if days > max_overdue_days:
                    max_overdue_days = days

        if max_overdue_days > 30:
            score += 35
            factors.append(f"Invoices critically overdue by > 30 days ({max_overdue_days}d, ₹{total_residual:,.2f}) [+35]")
        elif max_overdue_days >= 8:
            score += 25
            factors.append(f"Invoices severely overdue between 8-30 days ({max_overdue_days}d, ₹{total_residual:,.2f}) [+25]")
        elif max_overdue_days >= 1:
            score += 15
            factors.append(f"Invoices newly overdue between 1-7 days ({max_overdue_days}d, ₹{total_residual:,.2f}) [+15]")

        # 2. Failed payments in last 30 days
        thirty_days_ago = today - datetime.timedelta(days=30)
        pmt_domain = [
            ('partner_id', '=', partner_id),
            ('state', 'in', ['error', 'cancel', 'failed'])
        ]
        failed_payments = env['account.payment'].search(pmt_domain) if 'account.payment' in env else []
        recent_failed = [p for p in failed_payments if str(getattr(p, 'date', ''))[:10] >= str(thirty_days_ago)]
        if recent_failed:
            score += 20
            factors.append(f"{len(recent_failed)} failed/cancelled payment attempts in last 30 days [+20]")

        # 3. Renewal due within 7 days
        seven_days_ahead = today + datetime.timedelta(days=7)
        sub_domain = [
            ('partner_id', '=', partner_id),
            ('stage', 'in', ['in_progress', 'active'])
        ]
        active_subs = env['sale.order'].search(sub_domain) if 'sale.order' in env else []
        expiring_soon = False
        for s in active_subs:
            end_d = getattr(s, 'end_date', None) or getattr(s, 'next_invoice_date', None)
            if end_d:
                parsed_end = datetime.date.fromisoformat(str(end_d)[:10])
                if today <= parsed_end <= seven_days_ahead:
                    expiring_soon = True
                    break
        if expiring_soon:
            score += 15
            factors.append("Active subscription scheduled for renewal within 7 days [+15]")

        # 4. Unmatched transaction older than 7 days
        unmatched_domain = [('state', '=', 'unmatched')]
        unmatched = env['subscriptiq.payment.import.line'].search(unmatched_domain) if 'subscriptiq.payment.import.line' in env else []
        old_unmatched = False
        partner_obj = env['res.partner'].browse(partner_id)
        pname = getattr(partner_obj, 'name', '').lower()

        for u in unmatched:
            line_p = (getattr(u, 'partner_name', '') or '').lower()
            if pname and (pname in line_p or line_p in pname):
                tx_date = getattr(u, 'transaction_date', None)
                if tx_date:
                    tx_d = datetime.date.fromisoformat(str(tx_date)[:10])
                    if (today - tx_d).days >= 7:
                        old_unmatched = True
                        break
        if old_unmatched:
            score += 15
            factors.append("Unmatched bank transaction pending for >= 7 days [+15]")

        score = min(100, max(0, score))

        # Risk Level
        if score >= 80:
            level = 'critical'
        elif score >= 60:
            level = 'high'
        elif score >= 30:
            level = 'medium'
        else:
            level = 'low'

        return {
            'risk_score': score,
            'risk_level': level,
            'contributing_factors': factors if factors else ["No negative risk factors identified [0]"],
            'max_overdue_days': max_overdue_days,
            'outstanding_balance': total_residual
        }

class MLModelPipeline:
    """Local Scikit-Learn training, validation, comparison, and inference pipeline."""

    FEATURE_NAMES = [
        'overdue_invoice_count',
        'outstanding_balance',
        'failed_payment_count',
        'avg_payment_delay_days',
        'subscription_age_days',
        'previous_closure_count'
    ]

    @classmethod
    def extract_features(cls, env, partner_id, company_id=None):
        """Extracts normalized feature vector for a customer."""
        today = datetime.date.today()

        # Invoices
        inv_domain = [
            ('partner_id', '=', partner_id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted')
        ]
        invoices = env['account.move'].search(inv_domain) if 'account.move' in env else []
        overdue_count = 0
        outstanding_balance = 0.0
        delays = []

        for inv in invoices:
            residual = float(getattr(inv, 'amount_residual', 0.0))
            if residual > 0:
                outstanding_balance += residual
                due_d = getattr(inv, 'invoice_date_due', None)
                if due_d:
                    d = (today - datetime.date.fromisoformat(str(due_d)[:10])).days
                    if d > 0:
                        overdue_count += 1
                        delays.append(d)

        avg_delay = float(np.mean(delays)) if (SKLEARN_AVAILABLE and delays) else (sum(delays)/len(delays) if delays else 0.0)

        # Failed payments
        pmt_domain = [('partner_id', '=', partner_id), ('state', 'in', ['error', 'cancel', 'failed'])]
        failed_count = len(env['account.payment'].search(pmt_domain)) if 'account.payment' in env else 0

        # Subscriptions
        sub_domain = [('partner_id', '=', partner_id)]
        all_subs = env['sale.order'].search(sub_domain) if 'sale.order' in env else []
        closure_count = sum(1 for s in all_subs if getattr(s, 'stage', '') in ['closed', 'cancelled'])

        # Subscription age
        oldest_date = today
        for s in all_subs:
            sdate = getattr(s, 'date_order', None) or getattr(s, 'create_date', None)
            if sdate:
                sd = datetime.date.fromisoformat(str(sdate)[:10])
                if sd < oldest_date:
                    oldest_date = sd
        sub_age = (today - oldest_date).days

        return [
            float(overdue_count),
            float(outstanding_balance),
            float(failed_count),
            float(avg_delay),
            float(sub_age),
            float(closure_count)
        ]

    @classmethod
    def train_and_evaluate(cls, training_records: list):
        """
        Trains baseline Logistic Regression and Random Forest models on historical data.
        Evaluates Precision, Recall, ROC-AUC, and Brier calibration score.
        Returns evaluation metrics and selects champion model.
        """
        if not SKLEARN_AVAILABLE:
            return {'error': 'Scikit-learn not available', 'activated': False}

        if len(training_records) < 20:
            return {
                'error': f"Insufficient training data ({len(training_records)} records). Minimum 20 historical records required.",
                'activated': False,
                'fallback_to_rules': True
            }

        X = np.array([r['features'] for r in training_records])
        y = np.array([r['label'] for r in training_records])

        # Chronological train/test split (80/20)
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        # Check if validation set has both classes
        if len(np.unique(y_train)) < 2 or len(np.unique(y_val)) < 2:
            return {
                'error': 'Training or validation set does not contain both positive and negative churn outcomes.',
                'activated': False,
                'fallback_to_rules': True
            }

        # 1. Baseline: Logistic Regression
        lr = LogisticRegression(max_iter=1000, random_state=42)
        lr.fit(X_train, y_train)
        lr_pred = lr.predict(X_val)
        lr_prob = lr.predict_proba(X_val)[:, 1]

        lr_auc = float(roc_auc_score(y_val, lr_prob))
        lr_precision = float(precision_score(y_val, lr_pred, zero_division=0))
        lr_recall = float(recall_score(y_val, lr_pred, zero_division=0))
        lr_brier = float(brier_score_loss(y_val, lr_prob))

        # 2. Challenger: Random Forest (Tree-based model)
        rf = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
        rf.fit(X_train, y_train)
        rf_pred = rf.predict(X_val)
        rf_prob = rf.predict_proba(X_val)[:, 1]

        rf_auc = float(roc_auc_score(y_val, rf_prob))
        rf_precision = float(precision_score(y_val, rf_pred, zero_division=0))
        rf_recall = float(recall_score(y_val, rf_pred, zero_division=0))
        rf_brier = float(brier_score_loss(y_val, rf_prob))

        # Select champion
        champion_name = 'RandomForest' if rf_auc >= lr_auc else 'LogisticRegression'
        champion_model = rf if champion_name == 'RandomForest' else lr

        return {
            'success': True,
            'activated': True,
            'champion_model': champion_name,
            'model_object': champion_model,
            'metrics': {
                'baseline_logistic_regression': {
                    'roc_auc': round(lr_auc, 4),
                    'precision': round(lr_precision, 4),
                    'recall': round(lr_recall, 4),
                    'brier_calibration': round(lr_brier, 4)
                },
                'random_forest_tree': {
                    'roc_auc': round(rf_auc, 4),
                    'precision': round(rf_precision, 4),
                    'recall': round(rf_recall, 4),
                    'brier_calibration': round(rf_brier, 4)
                }
            },
            'dataset_size': len(training_records),
            'validation_size': len(y_val)
        }
