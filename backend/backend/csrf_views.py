from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie

@ensure_csrf_cookie
@require_http_methods(["GET"])
def get_csrf_token(request):
    """Get CSRF token for API testing"""
    token = get_token(request)
    return JsonResponse({'csrfToken': token})