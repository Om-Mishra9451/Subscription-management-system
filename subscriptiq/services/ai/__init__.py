"""
SubscriptIQ AI Provider Package
Free-Tier Intelligent Finance Copilot Architecture.
Only supports Groq, Google Gemini, and OpenRouter ($0/token free models).
"""

from .base_provider import BaseAIProvider, AIResponse
from .provider_manager import AIProviderManager
from .copilot_tools import CopilotToolRegistry
from .prompt_templates import COPILOT_SYSTEM_PROMPT

__all__ = [
    'BaseAIProvider',
    'AIResponse',
    'AIProviderManager',
    'CopilotToolRegistry',
    'COPILOT_SYSTEM_PROMPT'
]
