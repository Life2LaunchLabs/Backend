import os, sys
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

django_asgi_app = get_asgi_application()

# import AFTER django is ready
from apps.chat.websocket_urls import websocket_urlpatterns

# TEMP debug: prove this file is loaded
print(">>> USING ASGI:", __file__, file=sys.stderr, flush=True)

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})