import re
import uuid
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse

class InputValidator:
    @staticmethod
    def validate_uuid(value):
        """Validate UUID format"""
        try:
            uuid.UUID(value)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_decimal(value, min_val=0, max_val=None):
        """Validate decimal values"""
        try:
            decimal_val = Decimal(str(value))
            if decimal_val < min_val:
                return False
            if max_val and decimal_val > max_val:
                return False
            return True
        except (InvalidOperation, ValueError, TypeError):
            return False
    
    @staticmethod
    def sanitize_string(value, max_length=255):
        """Sanitize string input"""
        if not isinstance(value, str):
            return None
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', value.strip())
        return sanitized[:max_length] if len(sanitized) <= max_length else None
    
    @staticmethod
    def validate_username(username):
        """Validate username format"""
        if not isinstance(username, str):
            return False
        # Allow alphanumeric, underscore, hyphen
        pattern = r'^[a-zA-Z0-9_-]{3,50}$'
        return bool(re.match(pattern, username))
    
    @staticmethod
    def validate_required_fields(data, required_fields):
        """Validate required fields are present"""
        missing = [field for field in required_fields if field not in data or not data[field]]
        return missing

def validate_request_data(required_fields=None, optional_fields=None):
    """Decorator for request data validation"""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            try:
                import json
                body = json.loads(request.body)
            except (json.JSONDecodeError, ValueError):
                return JsonResponse({"error": "Invalid JSON format"}, status=400)
            
            if required_fields:
                missing = InputValidator.validate_required_fields(body, required_fields)
                if missing:
                    return JsonResponse({"error": f"Missing required fields: {', '.join(missing)}"}, status=400)
            
            # Add validated data to request
            request.validated_data = body
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator