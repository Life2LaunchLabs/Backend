"""
Debug middleware to trace WebSocket routing issues
"""
import logging

logger = logging.getLogger(__name__)

class WebSocketDebugMiddleware:
    """Middleware to debug WebSocket routing issues"""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'websocket':
            logger.info(f"🔍 WebSocket Debug - Full scope: {scope}")
            logger.info(f"🔍 WebSocket path: {scope.get('path', 'NO_PATH')}")
            logger.info(f"🔍 WebSocket query_string: {scope.get('query_string', b'').decode()}")
            logger.info(f"🔍 WebSocket headers: {dict(scope.get('headers', []))}")

            # Check if this looks like our expected pattern
            path = scope.get('path', '')
            if 'ws/chat/stream-chunked' in path:
                logger.info(f"✅ WebSocket path matches our pattern: {path}")
            else:
                logger.warning(f"❌ WebSocket path does NOT match our pattern: {path}")

        return await self.inner(scope, receive, send)