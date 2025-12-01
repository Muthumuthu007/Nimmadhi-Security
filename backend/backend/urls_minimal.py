"""
Minimal URL configuration for testing
"""
from django.urls import path
from django.http import JsonResponse

def health_check(request):
    """Simple health check endpoint"""
    return JsonResponse({"status": "ok", "message": "Django is running!"})

def csrf_token_simple(request):
    """Simple CSRF token endpoint"""
    from django.middleware.csrf import get_token
    token = get_token(request)
    return JsonResponse({'csrfToken': token})

urlpatterns = [
    path('', health_check, name='health_check'),
    path('health/', health_check, name='health_check_alt'),
    path('api/csrf-token/', csrf_token_simple, name='csrf_token'),
]