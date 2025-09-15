"""
ASGI config for mysite project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/asgi/
"""

import os
import logging
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Set up logging
logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Import websocket routing after Django is initialized
from apps.chat.websocket_urls import websocket_urlpatterns
from .debug_middleware import WebSocketDebugMiddleware

logger.info(f"WebSocket URL patterns loaded: {websocket_urlpatterns}")

class DebugURLRouter(URLRouter):
    def __init__(self, routes):
        super().__init__(routes)
        logger.info(f"DebugURLRouter initialized with {len(routes)} routes")
        for route in routes:
            logger.info(f"WebSocket route: {route.pattern}")

class DebugProtocolTypeRouter(ProtocolTypeRouter):
    async def __call__(self, scope, receive, send):
        logger.info(f"ASGI Request - Type: {scope['type']}, Path: {scope.get('path', 'N/A')}")
        if scope['type'] == 'websocket':
            logger.info(f"WebSocket connection attempt to: {scope['path']}")
            logger.info(f"WebSocket headers: {scope.get('headers', [])}")
        return await super().__call__(scope, receive, send)

application = WebSocketDebugMiddleware(
    DebugProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            DebugURLRouter(websocket_urlpatterns)
        ),
    })
)
