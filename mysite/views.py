from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime

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