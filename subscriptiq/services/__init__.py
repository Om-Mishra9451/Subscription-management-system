"""
SubscriptIQ Services Package
Export core revenue assurance services and adapters.
"""

from .odoo_adapter import models, fields, api, _, UserError, ValidationError, AccessError, round_currency
from .revenue_calculator import RevenueCalculator
from .rules_engine import RulesEngine
from .risk_engine import RiskEngine
from .billing_protection import BillingProtectionEngine
from .payment_matcher import PaymentMatcherEngine
from .churn_scoring import CustomerRiskScorer, MLModelPipeline
from .recovery_executor import RecoveryExecutor
from .finance_dashboard import FinanceDashboardService
from .ai import AIProviderManager, CopilotToolRegistry, COPILOT_SYSTEM_PROMPT

__all__ = [
    'models', 'fields', 'api', '_',
    'UserError', 'ValidationError', 'AccessError',
    'round_currency',
    'RevenueCalculator',
    'RulesEngine',
    'RiskEngine',
    'BillingProtectionEngine',
    'PaymentMatcherEngine',
    'CustomerRiskScorer',
    'MLModelPipeline',
    'RecoveryExecutor',
    'AIProviderManager',
    'CopilotToolRegistry',
    'COPILOT_SYSTEM_PROMPT'
]
