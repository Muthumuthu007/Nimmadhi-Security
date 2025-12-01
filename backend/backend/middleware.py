import time
import hashlib
from django.http import JsonResponse
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'RATE_LIMIT_ENABLE', True)
        self.rate_limit = getattr(settings, 'RATE_LIMIT_PER_MINUTE', 60)

    def __call__(self, request):
        if self.enabled and self.should_rate_limit(request):
            client_ip = self.get_client_ip(request)
            cache_key = f"rate_limit_{hashlib.md5(client_ip.encode()).hexdigest()}"
            
            current_requests = cache.get(cache_key, 0)
            
            if current_requests >= self.rate_limit:
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                return JsonResponse({
                    "error": "Rate limit exceeded. Please try again later."
                }, status=429)
            
            cache.set(cache_key, current_requests + 1, 60)  # 1 minute window
        
        response = self.get_response(request)
        return response
    
    def should_rate_limit(self, request):
        """Determine if request should be rate limited"""
        # Rate limit POST requests more strictly
        if request.method in ['POST', 'PUT', 'DELETE']:
            return True
        return False
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response