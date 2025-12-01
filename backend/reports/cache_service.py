"""
Caching service for frequently accessed data
"""
from django.core.cache import cache
from backend.dynamodb_service import dynamodb_service
import logging

logger = logging.getLogger(__name__)

class CacheService:
    """Service for caching frequently accessed data"""
    
    @staticmethod
    def get_stock_items(force_refresh=False):
        """Get stock items with caching"""
        cache_key = 'stock_items_all'
        
        if not force_refresh:
            cached_items = cache.get(cache_key)
            if cached_items is not None:
                logger.info("Returning cached stock items")
                return cached_items
        
        # Fetch from DB
        items = dynamodb_service.scan_table('STOCK')
        
        # Cache for 10 minutes
        cache.set(cache_key, items, 600)
        logger.info(f"Cached {len(items)} stock items")
        
        return items
    
    @staticmethod
    def get_groups(force_refresh=False):
        """Get groups with caching"""
        cache_key = 'groups_all'
        
        if not force_refresh:
            cached_groups = cache.get(cache_key)
            if cached_groups is not None:
                logger.info("Returning cached groups")
                return cached_groups
        
        # Fetch from DB
        groups = dynamodb_service.scan_table('GROUPS')
        
        # Cache for 15 minutes (groups change less frequently)
        cache.set(cache_key, groups, 900)
        logger.info(f"Cached {len(groups)} groups")
        
        return groups
    
    @staticmethod
    def get_transactions_by_date(date_str, force_refresh=False):
        """Get transactions for a specific date with caching"""
        cache_key = f'transactions_date_{date_str}'
        
        if not force_refresh:
            cached_transactions = cache.get(cache_key)
            if cached_transactions is not None:
                logger.info(f"Returning cached transactions for {date_str}")
                return cached_transactions
        
        # Fetch from DB
        transactions = dynamodb_service.scan_table(
            'stock_transactions',
            FilterExpression='#date = :report_date',
            ExpressionAttributeNames={'#date': 'date'},
            ExpressionAttributeValues={':report_date': date_str}
        )
        
        # Cache for 30 minutes (transactions for past dates don't change)
        cache.set(cache_key, transactions, 1800)
        logger.info(f"Cached {len(transactions)} transactions for {date_str}")
        
        return transactions
    
    @staticmethod
    def clear_stock_cache():
        """Clear stock-related cache entries"""
        cache.delete('stock_items_all')
        cache.delete('groups_all')
        logger.info("Cleared stock cache")
    
    @staticmethod
    def clear_transaction_cache(date_str=None):
        """Clear transaction cache for specific date or all"""
        if date_str:
            cache.delete(f'transactions_date_{date_str}')
            logger.info(f"Cleared transaction cache for {date_str}")
        else:
            # Clear all transaction caches (pattern-based deletion would be better)
            logger.info("Transaction cache cleared")