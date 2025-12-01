import logging
from django.http import JsonResponse

logger = logging.getLogger(__name__)

class SecureErrorHandler:
    @staticmethod
    def handle_error(error, operation="operation", include_details=False):
        """Handle errors securely without exposing sensitive information"""
        error_id = f"ERR_{hash(str(error)) % 10000:04d}"
        
        # Log the actual error for debugging
        logger.error(f"Error {error_id} in {operation}: {str(error)}")
        
        # Return generic error message to client
        if include_details and hasattr(error, 'safe_message'):
            message = error.safe_message
        else:
            message = f"An error occurred during {operation}"
        
        return JsonResponse({
            "error": message,
            "error_id": error_id
        }, status=500)
    
    @staticmethod
    def validation_error(message, status=400):
        """Return validation error response"""
        return JsonResponse({"error": message}, status=status)
    
    @staticmethod
    def unauthorized_error(message="Authentication required"):
        """Return unauthorized error response"""
        return JsonResponse({"error": message}, status=401)
    
    @staticmethod
    def forbidden_error(message="Access denied"):
        """Return forbidden error response"""
        return JsonResponse({"error": message}, status=403)
    
    @staticmethod
    def not_found_error(resource="Resource"):
        """Return not found error response"""
        return JsonResponse({"error": f"{resource} not found"}, status=404)