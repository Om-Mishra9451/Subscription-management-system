"""
SubscriptIQ AI Provider Manager
Implements multi-provider fallback orchestration:
Primary: Groq -> Secondary: Gemini -> Third: OpenRouter -> Graceful Error.
Handles HTTP 429, timeouts, exponential backoff with jitter, and credential privacy.
"""

import os
import time
import random
import logging
from typing import List, Dict, Any, Optional
from .base_provider import BaseAIProvider, AIResponse
from .groq_provider import GroqProvider
from .gemini_provider import GeminiProvider
from .openrouter_provider import OpenRouterProvider
from .copilot_tools import CopilotToolRegistry
from .prompt_templates import COPILOT_SYSTEM_PROMPT, sanitize_untrusted_input

_logger = logging.getLogger(__name__)

class AIProviderManager:
    """Manages free-tier AI providers, fallback chain, retries, and copilot execution."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        self.timeout = int(cfg.get('AI_TIMEOUT_SECONDS', os.getenv('AI_TIMEOUT_SECONDS', '30')))
        self.max_retries = int(cfg.get('AI_MAX_RETRIES', os.getenv('AI_MAX_RETRIES', '2')))

        # Primary & Fallback order
        primary = cfg.get('AI_PRIMARY_PROVIDER', os.getenv('AI_PRIMARY_PROVIDER', 'groq')).lower().strip()
        fallback_str = cfg.get('AI_FALLBACK_PROVIDERS', os.getenv('AI_FALLBACK_PROVIDERS', 'gemini,openrouter'))
        fallback_list = [p.strip().lower() for p in fallback_str.split(',') if p.strip()]

        self.provider_order = [primary] + [p for p in fallback_list if p != primary]

        # Initialize providers
        self.providers: Dict[str, BaseAIProvider] = {
            'groq': GroqProvider(
                api_key=cfg.get('GROQ_API_KEY', os.getenv('GROQ_API_KEY', '')),
                model=cfg.get('GROQ_MODEL', os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')),
                timeout=self.timeout
            ),
            'gemini': GeminiProvider(
                api_key=cfg.get('GEMINI_API_KEY', os.getenv('GEMINI_API_KEY', '')),
                model=cfg.get('GEMINI_MODEL', os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')),
                timeout=self.timeout
            ),
            'openrouter': OpenRouterProvider(
                api_key=cfg.get('OPENROUTER_API_KEY', os.getenv('OPENROUTER_API_KEY', '')),
                model=cfg.get('OPENROUTER_MODEL', os.getenv('OPENROUTER_MODEL', 'meta-llama/llama-3.3-70b-instruct:free')),
                timeout=self.timeout,
                free_only=str(cfg.get('OPENROUTER_FREE_MODELS_ONLY', os.getenv('OPENROUTER_FREE_MODELS_ONLY', 'true'))).lower() == 'true'
            )
        }

    def has_active_provider(self) -> bool:
        return any(p.is_configured() for p in self.providers.values())

    def execute_with_fallback(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> AIResponse:
        """
        Executes request through provider fallback chain:
        Groq -> Gemini -> OpenRouter -> Graceful error.
        Applies exponential backoff with jitter on 429 rate limit errors.
        """
        last_error = None

        for provider_name in self.provider_order:
            provider = self.providers.get(provider_name)
            if not provider or not provider.is_configured():
                continue

            for attempt in range(self.max_retries + 1):
                try:
                    _logger.info("Attempting AI generation with provider '%s' (model: %s, attempt: %d)",
                                 provider_name, provider.model, attempt + 1)
                    return provider.generate_response(messages, tools=tools)

                except Exception as e:
                    err_msg = str(e)
                    last_error = err_msg
                    is_rate_limit = "429" in err_msg or "rate limit" in err_msg.lower()

                    _logger.warning("Provider '%s' error on attempt %d: %s", provider_name, attempt + 1, err_msg)

                    if attempt < self.max_retries and is_rate_limit:
                        # Exponential backoff with jitter (1s, 2s, 4s... + random jitter)
                        backoff = (2 ** attempt) + random.uniform(0.1, 0.5)
                        _logger.info("Rate limit hit on '%s'; backing off for %.2fs before retry", provider_name, backoff)
                        time.sleep(backoff)
                    else:
                        break  # Fall back to next provider in priority chain

        # All providers exhausted or none configured
        sanitized_error = "Free-tier API credentials or quota error" if (last_error and "api key" in str(last_error).lower()) else (last_error or "No active providers")
        return AIResponse(
            content=f"[SubscriptIQ AI Copilot: Remote providers unavailable ({sanitized_error}). "
                    f"Operating in local deterministic mode using database records.]",
            provider_name="local_fallback",
            model="deterministic_rules"
        )

    def ask_copilot(self, env, user_query: str, user_id: int = 1, company_id: int = 1) -> Dict[str, Any]:
        """
        End-to-end Copilot pipeline:
        1. Sanitize user query against prompt injection.
        2. Provide system prompt and authorized tool schemas.
        3. Call LLM through fallback chain.
        4. If tool call generated, execute tool and provide final grounded answer.
        5. Return grounded response with source citations.
        """
        clean_query = sanitize_untrusted_input(user_query)
        tools = CopilotToolRegistry.get_tool_definitions()

        messages = [
            {"role": "system", "content": COPILOT_SYSTEM_PROMPT},
            {"role": "user", "content": clean_query}
        ]

        # First LLM call
        first_resp = self.execute_with_fallback(messages, tools=tools)

        # If running in local fallback, provide deterministic grounded answer based on query
        if first_resp.provider_name == "local_fallback":
            q_lower = clean_query.lower()
            if any(k in q_lower for k in ['revenue', 'mrr', 'arr', 'risk', 'metric']):
                data = CopilotToolRegistry.tool_get_revenue_summary(env, {}, user_id=user_id)
                answer = (
                    f"Based on real-time database records for Brightloop Software:\n"
                    f"• Monthly Recurring Revenue (MRR): ₹{data['mrr']:,.2f}\n"
                    f"• Annualized Recurring Revenue (ARR): ₹{data['arr']:,.2f}\n"
                    f"• Revenue at Risk: ₹{data['revenue_at_risk']:,.2f}\n"
                    f"• Verified Revenue Recovered: ₹{data['verified_recovered_revenue']:,.2f}\n"
                    f"• Revenue Leakage Rate: {data['leakage_rate']}"
                )
                return {"answer": answer, "tool_calls": [{"tool_name": "get_revenue_summary", "result": data}], "provider": "local_grounded", "model": "deterministic"}
            elif 'remind' in q_lower:
                # Find an open invoice to propose reminder for
                invs = env['account.move'].search([('move_type', '=', 'out_invoice'), ('amount_residual', '>', 0)]) if 'account.move' in env else []
                target_inv_id = invs[0].id if invs else 1
                prop = CopilotToolRegistry.tool_create_reminder_proposal(env, {'invoice_id': target_inv_id}, user_id=user_id)
                answer = (
                    f"Action Preview Prepared: {prop.get('message')}\n"
                    f"Action ID #{prop.get('action_id')} held in '{prop.get('state')}' state. "
                    f"Requires dual manager authorization prior to customer dispatch."
                )
                return {"answer": answer, "tool_calls": [{"tool_name": "create_reminder_proposal", "result": prop}], "provider": "local_grounded", "model": "deterministic"}
            else:
                return {
                    "answer": first_resp.content,
                    "tool_calls": [],
                    "provider": first_resp.provider_name,
                    "model": first_resp.model
                }

        if not first_resp.tool_calls:
            # Direct text answer without tools (or offline fallback)
            return {
                "answer": first_resp.content,
                "tool_calls": [],
                "provider": first_resp.provider_name,
                "model": first_resp.model
            }

        # Handle tool calls
        tool_results = []
        for tc in first_resp.tool_calls:
            tool_name = tc.get('name')
            tool_args = tc.get('arguments', {})
            _logger.info("Copilot executing authorized tool: %s with args: %s", tool_name, tool_args)

            result = CopilotToolRegistry.execute_tool(env, tool_name, tool_args, user_id=user_id)
            tool_results.append({
                "tool_name": tool_name,
                "arguments": tool_args,
                "result": result
            })

            # Append assistant message with tool call and tool response
            messages.append({
                "role": "assistant",
                "content": first_resp.content or f"Invoking tool {tool_name}..."
            })
            messages.append({
                "role": "user",
                "content": f"[Tool Output for {tool_name}]: {result}"
            })

        # Second LLM call for grounded synthesis
        try:
            final_resp = self.execute_with_fallback(messages)
            final_answer = final_resp.content
        except Exception:
            # If second synthesis fails, build structured deterministic summary from tool results
            final_answer = f"Tool '{tool_results[0]['tool_name']}' executed successfully. Results: {tool_results[0]['result']}"

        return {
            "answer": final_answer,
            "tool_calls": tool_results,
            "provider": first_resp.provider_name,
            "model": first_resp.model
        }
