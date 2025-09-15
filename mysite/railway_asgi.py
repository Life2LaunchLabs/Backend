"""
Railway-specific ASGI configuration
Alternative ASGI setup that may work better with Railway's WebSocket handling
"""

import os
import logging
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Set up logging
logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

# Initialize Django ASGI application early
django_asgi_app = get_asgi_application()

# Import websocket routing after Django is initialized
from apps.chat.websocket_urls import websocket_urlpatterns

logger.info("Railway ASGI: Initializing WebSocket routing")
logger.info(f"Railway ASGI: WebSocket patterns: {websocket_urlpatterns}")

# Simpler ASGI application without custom middleware for Railway
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})

logger.info("Railway ASGI: Application configured successfully")