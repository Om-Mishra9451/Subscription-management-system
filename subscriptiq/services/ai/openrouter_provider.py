"""
SubscriptIQ OpenRouter AI Provider (Third Provider)
Strictly integrates with verified $0/token free models on OpenRouter (e.g. meta-llama/llama-3.3-70b-instruct:free).
Rejects paid models automatically.
"""

import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from .base_provider import BaseAIProvider, AIResponse

_logger = logging.getLogger(__name__)

class OpenRouterProvider(BaseAIProvider):
    """OpenRouter Provider restricted to $0.00/token free models."""

    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: str = "", model: str = "", timeout: int = 30, free_only: bool = True):
        super().__init__(api_key=api_key, model=model, timeout=timeout)
        self.free_only = free_only
        self._validate_free_model_safety()

    def _validate_free_model_safety(self):
        """Ensures that only zero-cost models are invoked when free_only is set."""
        if self.free_only and self.model:
            # OpenRouter free tier models are tagged with ':free'
            if not self.model.endswith(':free'):
                _logger.warning("Configured OpenRouter model '%s' does not have ':free' suffix. Enforcing free tier safety.", self.model)

    @property
    def provider_name(self) -> str:
        return "openrouter"

    def health_check(self) -> bool:
        if not self.is_configured():
            return False
        try:
            resp = self.generate_response([{"role": "user", "content": "ping"}])
            return bool(resp and resp.content)
        except Exception as e:
            _logger.warning("OpenRouter health check failed: %s", str(e))
            return False

    def generate_response(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> AIResponse:
        if not self.is_configured():
            raise ValueError("OpenRouter API key or model is not configured.")

        # Hard safety enforcement against paid models
        target_model = self.model or "meta-llama/llama-3.3-70b-instruct:free"
        if self.free_only and not target_model.endswith(':free'):
            raise ValueError(f"OpenRouter model '{target_model}' rejected: OPENROUTER_FREE_MODELS_ONLY is enabled.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://brightloop.software/subscriptiq",
            "X-Title": "SubscriptIQ Autonomous Revenue Assurance"
        }

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 1024
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        data_bytes = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(self.API_URL, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
                choice = result['choices'][0]['message']
                content = choice.get('content') or ""
                tool_calls = []

                if 'tool_calls' in choice and choice['tool_calls']:
                    for tc in choice['tool_calls']:
                        fn = tc.get('function', {})
                        args = fn.get('arguments', '{}')
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except json.JSONDecodeError:
                                args = {}
                        tool_calls.append({
                            'id': tc.get('id', ''),
                            'name': fn.get('name', ''),
                            'arguments': args
                        })

                return AIResponse(
                    content=content,
                    tool_calls=tool_calls,
                    provider_name=self.provider_name,
                    model=target_model,
                    raw_response=result
                )
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='replace')
            if e.code == 429:
                _logger.warning("OpenRouter rate limit exceeded (HTTP 429)")
                raise RuntimeError(f"HTTP_429: Rate limit exceeded on OpenRouter: {err_body}")
            raise RuntimeError(f"OpenRouter API error ({e.code}): {err_body}")
        except Exception as e:
            raise RuntimeError(f"OpenRouter communication error: {str(e)}")
