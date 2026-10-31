"""
SubscriptIQ Google Gemini AI Provider (Secondary Provider)
Integrates with Google's Gemini free developer tier API.
Supports function calling and tool execution.
"""

import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from .base_provider import BaseAIProvider, AIResponse

_logger = logging.getLogger(__name__)

class GeminiProvider(BaseAIProvider):
    """Google Gemini Free Developer Tier Provider."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    @property
    def provider_name(self) -> str:
        return "gemini"

    def health_check(self) -> bool:
        if not self.is_configured():
            return False
        try:
            resp = self.generate_response([{"role": "user", "content": "ping"}])
            return bool(resp and resp.content)
        except Exception as e:
            _logger.warning("Gemini health check failed: %s", str(e))
            return False

    def generate_response(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> AIResponse:
        if not self.is_configured():
            raise ValueError("Gemini API key or model is not configured.")

        model_name = self.model or "gemini-2.0-flash"
        url = f"{self.BASE_URL}/{model_name}:generateContent?key={self.api_key}"

        # Convert OpenAI-style messages to Gemini contents
        contents = []
        system_instruction = None

        for msg in messages:
            role = msg.get('role')
            text = msg.get('content', '')
            if role == 'system':
                system_instruction = {"parts": [{"text": text}]}
            elif role == 'user':
                contents.append({"role": "user", "parts": [{"text": text}]})
            elif role == 'assistant':
                contents.append({"role": "model", "parts": [{"text": text}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1024
            }
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        # Convert OpenAI-style tools to Gemini function declarations if provided
        if tools:
            gemini_tools = []
            for t in tools:
                if t.get('type') == 'function':
                    fn = t.get('function', {})
                    gemini_tools.append({
                        "name": fn.get('name'),
                        "description": fn.get('description', ''),
                        "parameters": fn.get('parameters', {})
                    })
            if gemini_tools:
                payload["tools"] = [{"functionDeclarations": gemini_tools}]

        headers = {"Content-Type": "application/json"}
        data_bytes = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
                candidates = result.get('candidates', [])
                if not candidates:
                    return AIResponse(content="", provider_name=self.provider_name, model=model_name)

                parts = candidates[0].get('content', {}).get('parts', [])
                content_text = ""
                tool_calls = []

                for p in parts:
                    if 'text' in p:
                        content_text += p['text']
                    elif 'functionCall' in p:
                        fc = p['functionCall']
                        tool_calls.append({
                            'id': f"call_{fc.get('name')}",
                            'name': fc.get('name'),
                            'arguments': fc.get('args', {})
                        })

                return AIResponse(
                    content=content_text,
                    tool_calls=tool_calls,
                    provider_name=self.provider_name,
                    model=model_name,
                    raw_response=result
                )
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='replace')
            if e.code == 429:
                _logger.warning("Gemini rate limit exceeded (HTTP 429)")
                raise RuntimeError(f"HTTP_429: Rate limit exceeded on Gemini: {err_body}")
            raise RuntimeError(f"Gemini API error ({e.code}): {err_body}")
        except Exception as e:
            raise RuntimeError(f"Gemini communication error: {str(e)}")
