"""
Utility functions for user role management
"""
from backend.dynamodb_service import dynamodb_service
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

def get_user_role(username):
    """Get user role from DynamoDB"""
    try:
        user = dynamodb_service.get_item('USERS', {'username': username})
        if user:
            return user.get('role', 'user')  # Default to 'user' if role not found
        return None
    except ClientError as e:
        logger.error(f"Error getting user role for {username}: {e}")
        return None

def is_admin(username):
    """Check if user has admin role"""
    role = get_user_role(username)
    return role == 'admin'

def require_admin_role(username):
    """Decorator helper to check admin role"""
    return is_admin(username)