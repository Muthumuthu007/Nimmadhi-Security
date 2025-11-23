import boto3
from django.conf import settings
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

class DynamoDBService:
    def __init__(self):
        self.dynamodb = None
        self.tables = {}
        self._initialized = False
    
    def _initialize(self):
        if not self._initialized:
            try:
                self.dynamodb = boto3.resource(
                    'dynamodb',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
                for key, table_name in settings.DYNAMODB_TABLES.items():
                    self.tables[key] = self.dynamodb.Table(table_name)
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize DynamoDB: {e}")
                raise
    
    def get_table(self, table_key):
        self._initialize()
        table = self.tables.get(table_key)
        if table is None:
            raise ValueError(f"Table '{table_key}' not found in configuration")
        return table
    
    def put_item(self, table_key, item):
        try:
            table = self.get_table(table_key)
            response = table.put_item(Item=item)
            return response
        except ClientError as e:
            logger.error(f"Error putting item to {table_key}: {e}")
            raise
    
    def get_item(self, table_key, key):
        try:
            table = self.get_table(table_key)
            response = table.get_item(Key=key)
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Error getting item from {table_key}: {e}")
            raise
    
    def scan_table(self, table_key, **kwargs):
        try:
            table = self.get_table(table_key)
            response = table.scan(**kwargs)
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Error scanning {table_key}: {e}")
            raise
    
    def query_table(self, table_key, **kwargs):
        try:
            table = self.get_table(table_key)
            response = table.query(**kwargs)
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Error querying {table_key}: {e}")
            raise
    
    def delete_item(self, table_key, key):
        try:
            table = self.get_table(table_key)
            response = table.delete_item(Key=key)
            return response
        except ClientError as e:
            logger.error(f"Error deleting item from {table_key}: {e}")
            raise
    
    def update_item(self, table_key, key, update_expression, expression_attribute_values, **kwargs):
        try:
            table = self.get_table(table_key)
            response = table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                **kwargs
            )
            return response
        except ClientError as e:
            logger.error(f"Error updating item in {table_key}: {e}")
            raise

# Global instance
dynamodb_service = DynamoDBService()