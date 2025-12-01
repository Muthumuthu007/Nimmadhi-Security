from functools import wraps
from django.http import JsonResponse
from .jwt_utils import decode_jwt_token
from .token_manager import TokenManager
import logging

logger = logging.getLogger(__name__)

def jwt_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        token = auth_header.split(' ')[1]
        
        # Check if token is blacklisted
        if TokenManager.is_token_blacklisted(token):
            return JsonResponse({"error": "Token has been revoked"}, status=401)
        
        payload = decode_jwt_token(token)
        if not payload:
            return JsonResponse({"error": "Invalid or expired token"}, status=401)
        
        request.user_info = payload
        request.jwt_token = token  # Store for potential blacklisting
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        token = auth_header.split(' ')[1]
        payload = decode_jwt_token(token)
        
        if not payload:
            return JsonResponse({"error": "Invalid or expired token"}, status=401)
        
        if payload.get('role') != 'admin':
            return JsonResponse({"error": "Admin access required"}, status=403)
        
        request.user_info = payload
        return view_func(request, *args, **kwargs)
    return wrapper

def role_required(required_roles):
    """Decorator that requires specific roles"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if not auth_header or not auth_header.startswith('Bearer '):
                return JsonResponse({"error": "Authentication required"}, status=401)
            
            token = auth_header.split(' ')[1]
            payload = decode_jwt_token(token)
            
            if not payload:
                return JsonResponse({"error": "Invalid or expired token"}, status=401)
            
            user_role = payload.get('role')
            if user_role not in required_roles:
                return JsonResponse({"error": "Insufficient permissions"}, status=403)
            
            request.user_info = payload
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator