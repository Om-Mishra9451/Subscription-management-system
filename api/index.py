"""
Vercel Serverless Function Entrypoint for SubscriptIQ
Compatible with Vercel's Python Serverless Runtime.
Routes incoming HTTP requests to MasterServerHandler.
"""

import sys
import os

# Ensure project root is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from web_server import MasterServerHandler

# Vercel Python runtime detects BaseHTTPRequestHandler subclasses named `handler`
class handler(MasterServerHandler):
    pass

# Expose app for WSGI compatibility if needed
app = handler
