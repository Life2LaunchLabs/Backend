from django.urls import re_path
from . import websocket_consumers

websocket_urlpatterns = [
    re_path(r"^/ws/chat/stream/(?P<session_id>[-\w]+)/$", websocket_consumers.ChatStreamConsumer.as_asgi()),
    re_path(r"^/ws/chat/stream-chunked/(?P<session_id>[-\w]+)/$", websocket_consumers.ChatStreamConsumerWithChunking.as_asgi()),
    re_path(r"^/ws/chat/analytics/$", websocket_consumers.ChatAnalyticsConsumer.as_asgi()),
]