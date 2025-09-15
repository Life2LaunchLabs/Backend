"""
WebSocket URL routing for chat streaming
"""
from django.urls import re_path
from . import websocket_consumers

websocket_urlpatterns = [
    # Real-time chat streaming
    re_path(r"^ws/chat/stream/(?P<session_id>[-\w]+)/$", websocket_consumers.ChatStreamConsumer.as_asgi()),

    # Chunked streaming (for better UX simulation)
    re_path(r"^ws/chat/stream-chunked/(?P<session_id>[-\w]+)/$", websocket_consumers.ChatStreamConsumerWithChunking.as_asgi()),

    # Analytics streaming
    re_path(r"^ws/chat/analytics/$", websocket_consumers.ChatAnalyticsConsumer.as_asgi()),
]