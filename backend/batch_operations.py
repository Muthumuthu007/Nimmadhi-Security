#!/usr/bin/env python3
"""
Batch operations for ultra-fast data processing
"""

def batch_get_stock_items(item_ids):
    """Get multiple stock items in single batch request"""
    from backend.dynamodb_service import dynamodb_service
    
    # Convert to batch keys
    keys = [{'item_id': item_id} for item_id in item_ids]
    
    # Batch get (100x faster than individual gets)
    return dynamodb_service.batch_get_items('STOCK', keys)

def precompute_daily_aggregates():
    """Pre-compute daily aggregates for instant reports"""
    from datetime import datetime, timedelta
    from backend.dynamodb_service import dynamodb_service
    from collections import defaultdict
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Get today's transactions in parallel
    from concurrent.futures import ThreadPoolExecutor
    
    aggregates = {
        'inward_total': 0,
        'consumption_total': 0,
        'items_affected': 0
    }
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        inward_future = executor.submit(
            dynamodb_service.query_table,
            'stock_transactions',
            IndexName='OpTypeDateIndex',
            KeyConditionExpression='operation_type = :op AND #date = :date',
            ExpressionAttributeNames={'#date': 'date'},
            ExpressionAttributeValues={':op': 'AddStockQuantity', ':date': today}
        )
        
        consumption_future = executor.submit(
            dynamodb_service.query_table,
            'stock_transactions',
            IndexName='OpTypeDateIndex', 
            KeyConditionExpression='operation_type = :op AND #date = :date',
            ExpressionAttributeNames={'#date': 'date'},
            ExpressionAttributeValues={':op': 'PushToProduction', ':date': today}
        )
        
        inward_txns = inward_future.result()
        consumption_txns = consumption_future.result()
    
    # Fast aggregation
    for txn in inward_txns:
        details = txn.get('details', {})
        aggregates['inward_total'] += float(details.get('quantity_added', 0))
    
    for txn in consumption_txns:
        details = txn.get('details', {})
        deductions = details.get('deductions', {})
        aggregates['consumption_total'] += sum(float(v) for v in deductions.values())
    
    aggregates['items_affected'] = len(set(
        [txn.get('details', {}).get('item_id') for txn in inward_txns + consumption_txns]
    ))
    
    return aggregates

if __name__ == "__main__":
    print("⚡ Testing batch operations...")
    result = precompute_daily_aggregates()
    print(f"📊 Today's aggregates: {result}")
    print("🚀 Batch operations ready!")