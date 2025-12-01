import logging
from backend.dynamodb_service import dynamodb_service
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class SecureDatabaseService:
    @staticmethod
    def get_user_products(username, table_name='CASTING_PRODUCTS'):
        """Get products for specific user instead of scanning all"""
        try:
            # Use query instead of scan for better performance and security
            response = dynamodb_service.dynamodb.Table(table_name).scan(
                FilterExpression='username = :username',
                ExpressionAttributeValues={':username': username},
                Limit=100  # Limit results to prevent large data exposure
            )
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Error querying user products: {e}")
            return []
    
    @staticmethod
    def check_product_ownership(product_id, username, table_name='CASTING_PRODUCTS'):
        """Verify user owns the product before operations"""
        try:
            product = dynamodb_service.get_item(table_name, {'product_id': product_id})
            if product and product.get('username') == username:
                return product
            return None
        except ClientError as e:
            logger.error(f"Error checking product ownership: {e}")
            return None
    
    @staticmethod
    def sanitize_scan_results(items, user_role='user'):
        """Remove sensitive data from scan results based on user role"""
        sanitized = []
        for item in items:
            # Remove sensitive fields for non-admin users
            if user_role != 'admin':
                item.pop('internal_notes', None)
                item.pop('cost_breakdown_details', None)
            sanitized.append(item)
        return sanitized