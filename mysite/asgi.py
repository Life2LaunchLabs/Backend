import os
import sys
import logging

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

django_asgi_app = get_asgi_application()

# Import websocket routes
from apps.chat.websocket_urls import websocket_urlpatterns


class DebugProtocolTypeRouter(ProtocolTypeRouter):
    async def __call__(self, scope, receive, send):
        # Print raw ASGI scope info to stdout
        print(">>> DEBUG: incoming scope <<<", file=sys.stderr)
        print("  type:", scope.get("type"), file=sys.stderr)
        print("  path:", scope.get("path"), file=sys.stderr)
        print("  headers:", scope.get("headers"), file=sys.stderr)
        print("  method:", scope.get("method"), file=sys.stderr)
        print("  query_string:", scope.get("query_string"), file=sys.stderr)
        print(">>> END DEBUG <<<", file=sys.stderr)

        return await super().__call__(scope, receive, send)


application = DebugProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})