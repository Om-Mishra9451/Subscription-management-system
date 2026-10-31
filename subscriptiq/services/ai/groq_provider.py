"""
SubscriptIQ Groq AI Provider (Primary Provider)
Integrates with Groq's high-speed free developer tier API.
Supports function calling and tool execution.
"""

import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from .base_provider import BaseAIProvider, AIResponse

_logger = logging.getLogger(__name__)

class GroqProvider(BaseAIProvider):
    """Groq Free Developer Tier Provider."""

    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    @property
    def provider_name(self) -> str:
        return "groq"

    def health_check(self) -> bool:
        if not self.is_configured():
            return False
        try:
            resp = self.generate_response([{"role": "user", "content": "ping"}])
            return bool(resp and resp.content)
        except Exception as e:
            _logger.warning("Groq health check failed: %s", str(e))
            return False

    def generate_response(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> AIResponse:
        if not self.is_configured():
            raise ValueError("Groq API key or model is not configured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "SubscriptIQ-Revenue-Assurance/1.0"
        }

        payload: Dict[str, Any] = {
            "model": self.model or "llama-3.3-70b-versatile",
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
                    model=self.model,
                    raw_response=result
                )
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='replace')
            if e.code == 429:
                _logger.warning("Groq rate limit exceeded (HTTP 429)")
                raise RuntimeError(f"HTTP_429: Rate limit exceeded on Groq: {err_body}")
            raise RuntimeError(f"Groq API error ({e.code}): {err_body}")
        except Exception as e:
            raise RuntimeError(f"Groq communication error: {str(e)}")
