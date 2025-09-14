"""
WebSocket URL routing for chat streaming
"""
from django.urls import path
from . import websocket_consumers

websocket_urlpatterns = [
    # Real-time chat streaming
    path('ws/chat/stream/<str:session_id>/', websocket_consumers.ChatStreamConsumer.as_asgi()),
    
    # Chunked streaming (for better UX simulation)
    path('ws/chat/stream-chunked/<str:session_id>/', websocket_consumers.ChatStreamConsumerWithChunking.as_asgi()),
    
    # Analytics streaming
    path('ws/chat/analytics/', websocket_consumers.ChatAnalyticsConsumer.as_asgi()),
]