import boto3
from django.conf import settings
from django.core.cache import cache
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
                # Use session with connection pooling
                session = boto3.Session(
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
                
                self.dynamodb = session.resource(
                    'dynamodb',
                    config=boto3.session.Config(
                        max_pool_connections=50,
                        retries={'max_attempts': 3, 'mode': 'adaptive'}
                    )
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
            
            # Enhanced caching with better key generation
            cache_key = f"scan_{table_key}_{hash(str(sorted(kwargs.items())))}"
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Use parallel scan for large tables
            if not kwargs.get('FilterExpression') and table_key in ['stock_transactions', 'STOCK']:
                items = self._parallel_scan(table, **kwargs)
            else:
                response = table.scan(**kwargs)
                items = response.get('Items', [])
                
                while 'LastEvaluatedKey' in response:
                    kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
                    response = table.scan(**kwargs)
                    items.extend(response.get('Items', []))
            
            # Cache results for 2 minutes
            cache.set(cache_key, items, 120)
            return items
        except ClientError as e:
            logger.error(f"Error scanning {table_key}: {e}")
            raise
    
    def _parallel_scan(self, table, **kwargs):
        """Parallel scan for better performance on large tables"""
        import concurrent.futures
        
        segments = 4  # Number of parallel segments
        items = []
        
        def scan_segment(segment):
            segment_kwargs = kwargs.copy()
            segment_kwargs.update({
                'Segment': segment,
                'TotalSegments': segments
            })
            
            response = table.scan(**segment_kwargs)
            segment_items = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                segment_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
                response = table.scan(**segment_kwargs)
                segment_items.extend(response.get('Items', []))
            
            return segment_items
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=segments) as executor:
            futures = [executor.submit(scan_segment, i) for i in range(segments)]
            for future in concurrent.futures.as_completed(futures):
                items.extend(future.result())
        
        return items
    
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
            
            # Clear related cache entries
            cache_pattern = f"scan_{table_key}_*"
            cache.delete_many([cache_pattern])
            
            return response
        except ClientError as e:
            logger.error(f"Error updating item in {table_key}: {e}")
            raise
    
    def batch_get_items(self, table_key, keys):
        """Efficiently get multiple items at once"""
        try:
            table = self.get_table(table_key)
            
            # DynamoDB batch_get_item has a limit of 100 items
            items = []
            for i in range(0, len(keys), 100):
                batch_keys = keys[i:i+100]
                response = self.dynamodb.batch_get_item(
                    RequestItems={
                        table.name: {
                            'Keys': batch_keys
                        }
                    }
                )
                items.extend(response.get('Responses', {}).get(table.name, []))
            
            return items
        except ClientError as e:
            logger.error(f"Error batch getting items from {table_key}: {e}")
            raise

# Global instance
dynamodb_service = DynamoDBService()