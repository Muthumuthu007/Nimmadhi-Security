import time
import logging
from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger(__name__)

class SecurityMonitor:
    FAILED_LOGIN_PREFIX = "failed_login_"
    SUSPICIOUS_ACTIVITY_PREFIX = "suspicious_"
    
    @staticmethod
    def record_failed_login(ip_address, username=None):
        """Record failed login attempt"""
        key = f"{SecurityMonitor.FAILED_LOGIN_PREFIX}{ip_address}"
        attempts = cache.get(key, 0) + 1
        cache.set(key, attempts, 300)  # 5 minutes
        
        if attempts >= 5:
            logger.warning(f"Multiple failed login attempts from IP: {ip_address}, Username: {username}")
            SecurityMonitor.record_suspicious_activity(ip_address, "multiple_failed_logins")
        
        return attempts
    
    @staticmethod
    def record_suspicious_activity(ip_address, activity_type):
        """Record suspicious activity"""
        key = f"{SecurityMonitor.SUSPICIOUS_ACTIVITY_PREFIX}{ip_address}"
        activities = cache.get(key, [])
        activities.append({
            'type': activity_type,
            'timestamp': time.time()
        })
        cache.set(key, activities, 3600)  # 1 hour
        
        logger.warning(f"Suspicious activity detected - IP: {ip_address}, Type: {activity_type}")
    
    @staticmethod
    def is_ip_blocked(ip_address):
        """Check if IP should be temporarily blocked"""
        failed_attempts = cache.get(f"{SecurityMonitor.FAILED_LOGIN_PREFIX}{ip_address}", 0)
        return failed_attempts >= 10  # Block after 10 failed attempts
    
    @staticmethod
    def record_security_event(event_type, user=None, ip_address=None, details=None):
        """Record security events for monitoring"""
        logger.info(f"Security Event - Type: {event_type}, User: {user}, IP: {ip_address}, Details: {details}")

def security_monitor_middleware(get_response):
    """Middleware to monitor security events"""
    def middleware(request):
        ip_address = request.META.get('REMOTE_ADDR')
        
        # Check if IP is blocked
        if SecurityMonitor.is_ip_blocked(ip_address):
            logger.warning(f"Blocked request from IP: {ip_address}")
            return JsonResponse({"error": "Access temporarily blocked"}, status=429)
        
        response = get_response(request)
        
        # Monitor failed authentication
        if response.status_code == 401:
            SecurityMonitor.record_failed_login(ip_address)
        
        return response
    
    return middleware