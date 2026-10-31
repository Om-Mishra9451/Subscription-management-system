"""
SubscriptIQ Copilot Web & API Controller
Provides secure endpoints for the interactive AI Finance Copilot interface.
Enforces authentication, prompt sanitization, grounded responses, and audit logging.
"""

import json
import logging
from ..services.odoo_adapter import HAS_NATIVE_ODOO

_logger = logging.getLogger(__name__)

if HAS_NATIVE_ODOO:
    from odoo import http
    from odoo.http import request
else:
    class DummyHttp:
        @staticmethod
        def route(*args, **kwargs):
            def decorator(f):
                return f
            return decorator

        class Controller:
            pass

    http = DummyHttp()
    request = None

from ..services.ai import AIProviderManager

class CopilotController(http.Controller):

    @http.route('/subscriptiq/copilot/ask', type='json', auth='user', methods=['POST'], csrf=False)
    def ask_copilot_endpoint(self, **kwargs):
        """
        Receives user prompt, executes through provider manager with fallback,
        logs interaction, and returns grounded answer.
        """
        query = kwargs.get('query') or (request.jsonrequest.get('query') if request and hasattr(request, 'jsonrequest') else '')
        if not query:
            return {'error': 'Query text is required.'}

        env = request.env if request and hasattr(request, 'env') else None
        user_id = env.uid if env else 1
        company_id = env.company.id if env and hasattr(env, 'company') and env.company else 1

        manager = AIProviderManager()
        result = manager.ask_copilot(env, user_query=query, user_id=user_id, company_id=company_id)

        # Log copilot query
        if env and 'subscriptiq.copilot.log' in env.registry:
            env['subscriptiq.copilot.log'].create({
                'user_id': user_id,
                'company_id': company_id,
                'query': query,
                'response': result.get('answer'),
                'provider': result.get('provider'),
                'model': result.get('model'),
                'tool_calls': json.dumps(result.get('tool_calls', []))
            })

        return result
