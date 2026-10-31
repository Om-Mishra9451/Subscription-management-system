"""
SubscriptIQ Copilot Tool Whitelist & Structured Dispatcher
Exposes strictly authorized, structured, grounded database query functions to the AI Copilot.
Prevents arbitrary execution. Enforces two-phase approval proposals for write actions.
"""

import datetime
from decimal import Decimal
from typing import Dict, Any, List
from ..revenue_calculator import RevenueCalculator
from ..churn_scoring import CustomerRiskScorer
from ..recovery_executor import RecoveryExecutor

class CopilotToolRegistry:
    """Explicitly whitelisted read and proposal tools for the AI Copilot."""

    @classmethod
    def get_tool_definitions(cls) -> List[Dict[str, Any]]:
        """Returns JSON schema definitions of all whitelisted tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_dashboard_metrics",
                    "description": "Fetch high-level revenue assurance metrics: Verified Revenue Recovered, Revenue at Risk, Leakage Rate, MRR, ARR, and active subscription count.",
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_revenue_summary",
                    "description": "Get detailed recurring revenue breakdown, overdue debt total, and risk by category.",
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_overdue_invoices",
                    "description": "List invoices currently overdue, with customer name, days overdue, residual amount, and source record ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "description": "Max records to return (default 5)"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_active_subscriptions",
                    "description": "List currently active customer subscriptions with recurring amounts and billing intervals.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "description": "Max records to return (default 5)"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_expiring_subscriptions",
                    "description": "List subscriptions that will expire within the given number of days.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "days_ahead": {"type": "integer", "description": "Days lookahead window (default 7)"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_customer_risk_details",
                    "description": "Get detailed explainable risk breakdown and contributing factors for a specific customer.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "partner_id": {"type": "integer", "description": "Odoo customer ID"}
                        },
                        "required": ["partner_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_unmatched_payments",
                    "description": "List imported bank transactions awaiting reconciliation matching.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "description": "Max records to return"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_recovery_actions",
                    "description": "List pending, approved, and completed recovery actions in the system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "state": {"type": "string", "enum": ["awaiting_approval", "approved", "completed", "failed", "all"]}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_reminder_proposal",
                    "description": "Prepare a payment reminder action proposal for an overdue customer. Requires human authorization.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "invoice_id": {"type": "integer", "description": "Target overdue invoice ID"},
                            "customer_id": {"type": "integer", "description": "Customer partner ID"}
                        },
                        "required": ["invoice_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_renewal_offer_draft",
                    "description": "Prepare a draft renewal quotation proposal for an expiring subscription. Requires human authorization.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subscription_id": {"type": "integer", "description": "Target subscription ID"}
                        },
                        "required": ["subscription_id"]
                    }
                }
            }
        ]

    @classmethod
    def execute_tool(cls, env, tool_name: str, arguments: Dict[str, Any], user_id: int = 1) -> Dict[str, Any]:
        """Dispatches authorized tool execution against the database."""
        if not hasattr(cls, f"tool_{tool_name}"):
            return {"error": f"Tool '{tool_name}' is not in the authorized whitelist."}

        handler = getattr(cls, f"tool_{tool_name}")
        return handler(env, arguments, user_id=user_id)

    # 1. Dashboard Metrics
    @classmethod
    def tool_get_dashboard_metrics(cls, env, args, user_id=1):
        metrics = RevenueCalculator.compute_dashboard_metrics(env)
        return {"status": "success", "metrics": metrics}

    # 2. Revenue Summary
    @classmethod
    def tool_get_revenue_summary(cls, env, args, user_id=1):
        metrics = RevenueCalculator.compute_dashboard_metrics(env)
        return {
            "status": "success",
            "mrr": metrics['mrr'],
            "arr": metrics['arr'],
            "revenue_at_risk": metrics['revenue_at_risk'],
            "verified_recovered_revenue": metrics['verified_recovered_revenue'],
            "leakage_rate": f"{metrics['revenue_leakage_rate']}%",
            "risk_breakdown": metrics['risk_breakdown']
        }

    # 3. Overdue Invoices
    @classmethod
    def tool_get_overdue_invoices(cls, env, args, user_id=1):
        limit = args.get('limit', 5)
        today = datetime.date.today()
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('amount_residual', '>', 0.0)
        ]
        invoices = env['account.move'].search(domain) if 'account.move' in env.registry else []
        results = []
        for inv in invoices:
            due_d_str = getattr(inv, 'invoice_date_due', None)
            if due_d_str:
                due_d = datetime.date.fromisoformat(str(due_d_str)[:10])
                if due_d < today:
                    partner = inv.partner_id
                    results.append({
                        "invoice_id": inv.id,
                        "invoice_number": inv.name,
                        "customer_id": partner.id if hasattr(partner, 'id') else partner,
                        "customer_name": getattr(partner, 'name', 'Unknown'),
                        "residual_amount": float(getattr(inv, 'amount_residual', 0.0)),
                        "total_amount": float(getattr(inv, 'amount_total', 0.0)),
                        "due_date": str(due_d),
                        "days_overdue": (today - due_d).days
                    })
        results.sort(key=lambda x: x['days_overdue'], reverse=True)
        return {"status": "success", "count": len(results), "invoices": results[:limit]}

    # 4. Active Subscriptions
    @classmethod
    def tool_get_active_subscriptions(cls, env, args, user_id=1):
        limit = args.get('limit', 5)
        domain = [('stage', 'in', ['in_progress', 'active'])]
        subs = env['sale.order'].search(domain) if 'sale.order' in env.registry else []
        results = []
        for s in subs[:limit]:
            partner = s.partner_id
            plan = getattr(s, 'plan_id', None)
            results.append({
                "subscription_id": s.id,
                "name": s.name,
                "customer_name": getattr(partner, 'name', 'Unknown'),
                "plan_name": getattr(plan, 'name', 'Standard Plan') if plan else 'Standard',
                "recurring_amount": float(getattr(s, 'recurring_total', getattr(s, 'amount_total', 0.0))),
                "start_date": str(getattr(s, 'start_date', ''))[:10],
                "stage": getattr(s, 'stage', 'active')
            })
        return {"status": "success", "count": len(results), "subscriptions": results}

    # 5. Expiring Subscriptions
    @classmethod
    def tool_get_expiring_subscriptions(cls, env, args, user_id=1):
        days_ahead = args.get('days_ahead', 7)
        today = datetime.date.today()
        target_date = today + datetime.timedelta(days=days_ahead)

        domain = [('stage', 'in', ['in_progress', 'active'])]
        subs = env['sale.order'].search(domain) if 'sale.order' in env.registry else []
        expiring = []
        for s in subs:
            end_date = getattr(s, 'end_date', None) or getattr(s, 'next_invoice_date', None)
            if end_date:
                ed = datetime.date.fromisoformat(str(end_date)[:10])
                if today <= ed <= target_date:
                    partner = s.partner_id
                    expiring.append({
                        "subscription_id": s.id,
                        "name": s.name,
                        "customer_name": getattr(partner, 'name', 'Unknown'),
                        "expiry_date": str(ed),
                        "days_remaining": (ed - today).days,
                        "recurring_amount": float(getattr(s, 'recurring_total', getattr(s, 'amount_total', 0.0)))
                    })
        return {"status": "success", "expiring_count": len(expiring), "subscriptions": expiring}

    # 6. Customer Risk Details
    @classmethod
    def tool_get_customer_risk_details(cls, env, args, user_id=1):
        partner_id = args.get('partner_id')
        partner = env['res.partner'].browse(partner_id)
        if not partner.exists():
            return {"error": f"Customer ID {partner_id} not found."}
        risk_data = CustomerRiskScorer.calculate_deterministic_score(env, partner_id)
        return {
            "status": "success",
            "customer_id": partner_id,
            "customer_name": getattr(partner, 'name', ''),
            "risk_score": risk_data['risk_score'],
            "risk_level": risk_data['risk_level'],
            "contributing_factors": risk_data['contributing_factors'],
            "outstanding_balance": risk_data['outstanding_balance']
        }

    # 7. Unmatched Payments
    @classmethod
    def tool_get_unmatched_payments(cls, env, args, user_id=1):
        limit = args.get('limit', 5)
        domain = [('state', '=', 'unmatched')]
        lines = env['subscriptiq.payment.import.line'].search(domain) if 'subscriptiq.payment.import.line' in env.registry else []
        results = []
        for l in lines[:limit]:
            results.append({
                "import_line_id": l.id,
                "transaction_id": l.external_transaction_id,
                "amount": float(l.amount),
                "date": str(l.transaction_date)[:10],
                "reference": l.reference,
                "partner_name": l.partner_name
            })
        return {"status": "success", "count": len(results), "unmatched_transactions": results}

    # 8. Recovery Actions
    @classmethod
    def tool_get_recovery_actions(cls, env, args, user_id=1):
        state = args.get('state', 'all')
        domain = []
        if state != 'all':
            domain.append(('state', '=', state))
        actions = env['subscriptiq.action'].search(domain) if 'subscriptiq.action' in env.registry else []
        results = []
        for a in actions:
            results.append({
                "action_id": a.id,
                "name": a.name,
                "action_type": a.action_type,
                "state": a.state,
                "idempotency_key": getattr(a, 'idempotency_key', '')
            })
        return {"status": "success", "count": len(results), "actions": results}

    # 9. Create Reminder Proposal (Two-Phase Approval)
    @classmethod
    def tool_create_reminder_proposal(cls, env, args, user_id=1):
        inv_id = args.get('invoice_id')
        inv = env['account.move'].browse(inv_id)
        if not inv.exists():
            return {"error": f"Invoice ID {inv_id} not found."}

        # Find risk case for this invoice
        risk_cases = env['subscriptiq.risk.case'].search([('invoice_id', '=', inv_id)]) if 'subscriptiq.risk.case' in env.registry else []
        rc_ids = risk_cases.ids if risk_cases else []

        cust_id = inv.partner_id.id if hasattr(inv.partner_id, 'id') else inv.partner_id
        action = RecoveryExecutor.propose_action(
            env,
            action_type='bulk_reminder_campaign',
            risk_case_ids=rc_ids,
            payload={'invoice_id': inv_id, 'invoice_name': inv.name, 'customer_id': cust_id},
            user_id=user_id,
            company_id=inv.company_id.id if hasattr(inv.company_id, 'id') else 1
        )

        return {
            "status": "proposal_created",
            "message": f"Reminder proposal drafted for Invoice {inv.name}. Requires user authorization before dispatch.",
            "action_id": action.id,
            "action_name": action.name,
            "state": action.state,
            "requires_approval": True
        }

    # 10. Create Renewal Offer Draft (Two-Phase Approval)
    @classmethod
    def tool_create_renewal_offer_draft(cls, env, args, user_id=1):
        sub_id = args.get('subscription_id')
        sub = env['sale.order'].browse(sub_id)
        if not sub.exists():
            return {"error": f"Subscription ID {sub_id} not found."}

        sub_cust_id = sub.partner_id.id if hasattr(sub.partner_id, 'id') else sub.partner_id
        action = RecoveryExecutor.propose_action(
            env,
            action_type='approve_renewal_offer',
            payload={'subscription_id': sub_id, 'subscription_name': sub.name, 'customer_id': sub_cust_id},
            user_id=user_id,
            company_id=sub.company_id.id if hasattr(sub.company_id, 'id') else 1
        )

        return {
            "status": "proposal_created",
            "message": f"Renewal quotation proposal drafted for Subscription {sub.name}. Requires user approval before confirmation.",
            "action_id": action.id,
            "action_name": action.name,
            "state": action.state,
            "requires_approval": True
        }
