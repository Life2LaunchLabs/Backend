from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """Simple health check endpoint to verify frontend-backend connectivity"""
    return JsonResponse({
        'status': 'ok',
        'message': 'Backend is running and accessible!',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

def websocket_debug(request, path):
    """Debug view to catch WebSocket requests hitting HTTP router"""
    logger.error(f"🚨 WebSocket request hit HTTP router! Path: ws/{path}")
    logger.error(f"🚨 Request headers: {dict(request.headers)}")
    logger.error(f"🚨 Request method: {request.method}")
    logger.error(f"🚨 Is WebSocket upgrade? {'upgrade' in str(request.headers).lower()}")

    return JsonResponse({
        "error": "WebSocket request incorrectly routed to HTTP",
        "path": f"ws/{path}",
        "help": "This should be handled by ASGI WebSocket router",
        "headers": dict(request.headers)
    }, status=400)