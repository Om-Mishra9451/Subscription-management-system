"""
SubscriptIQ Abstract AI Provider
Base contract for free-tier LLM integrations.
"""

from typing import List, Dict, Any, Optional

class AIResponse:
    """Standardized response from AI providers."""
    def __init__(self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None,
                 provider_name: str = "", model: str = "", raw_response: Any = None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.provider_name = provider_name
        self.model = model
        self.raw_response = raw_response

    def to_dict(self) -> Dict[str, Any]:
        return {
            'content': self.content,
            'tool_calls': self.tool_calls,
            'provider': self.provider_name,
            'model': self.model
        }

class BaseAIProvider:
    """Abstract provider interface."""
    def __init__(self, api_key: str = "", model: str = "", timeout: int = 30):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        raise NotImplementedError

    def is_configured(self) -> bool:
        return bool(self.api_key and self.model)

    def health_check(self) -> bool:
        """Lightweight check to verify connectivity and authentication."""
        raise NotImplementedError

    def generate_response(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> AIResponse:
        """Generates completion or tool call."""
        raise NotImplementedError
