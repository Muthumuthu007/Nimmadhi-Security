#!/usr/bin/env python3
"""
Script to check inward stock transactions for a specific date
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.dynamodb_service import dynamodb_service
from boto3.dynamodb.conditions import Attr
from datetime import datetime

def check_inward_transactions(date_str):
    """Check if there are any AddStockQuantity transactions for the given date"""
    print(f"\n{'='*60}")
    print(f"Checking Inward Transactions for: {date_str}")
    print(f"{'='*60}\n")
    
    # Get all AddStockQuantity transactions
    print("1. Fetching all AddStockQuantity transactions...")
    all_transactions = dynamodb_service.scan_table(
        'stock_transactions',
        FilterExpression=Attr('operation_type').eq('AddStockQuantity')
    )
    print(f"   Total AddStockQuantity transactions: {len(all_transactions)}")
    
    # Filter by date
    date_transactions = [
        tx for tx in all_transactions 
        if tx.get('date') == date_str
    ]
    print(f"   Transactions on {date_str}: {len(date_transactions)}")
    
    if date_transactions:
        print(f"\n2. Transaction Details:")
        for i, tx in enumerate(date_transactions, 1):
            print(f"\n   Transaction #{i}:")
            print(f"   - Transaction ID: {tx.get('transaction_id')}")
            print(f"   - Date: {tx.get('date')}")
            print(f"   - Timestamp: {tx.get('timestamp')}")
            
            details = tx.get('details', {})
            print(f"   - Item ID: {details.get('item_id')}")
            print(f"   - Quantity Added: {details.get('quantity_added')}")
            print(f"   - Cost Per Unit: {details.get('cost_per_unit')}")
            print(f"   - GST Percentage: {details.get('gst_percentage')}")
            print(f"   - GST Amount: {details.get('gst_amount')}")
            print(f"   - Added Cost: {details.get('added_cost')}")
            print(f"   - Supplier: {details.get('supplier_name')}")
    else:
        print(f"\n   ❌ No inward transactions found for {date_str}")
        
        # Show recent transactions
        print(f"\n3. Recent AddStockQuantity transactions (last 10):")
        sorted_txns = sorted(all_transactions, key=lambda x: x.get('timestamp', ''), reverse=True)[:10]
        for tx in sorted_txns:
            print(f"   - {tx.get('date')} | {tx.get('details', {}).get('item_id')} | Qty: {tx.get('details', {}).get('quantity_added')}")
    
    # Check stock items
    print(f"\n4. Checking STOCK table...")
    stocks = dynamodb_service.scan_table('STOCK')
    print(f"   Total stock items: {len(stocks)}")
    
    if stocks:
        print(f"\n   Sample stock items (first 5):")
        for stock in stocks[:5]:
            print(f"   - {stock.get('item_id')} | Qty: {stock.get('quantity')} | GST: {stock.get('gst_percentage')}%")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    # Check for the date from command line or use default
    if len(sys.argv) > 1:
        date_to_check = sys.argv[1]
    else:
        date_to_check = "2025-12-03"
    
    check_inward_transactions(date_to_check)
    
    # Also check today's date
    today = datetime.now().strftime("%Y-%m-%d")
    if today != date_to_check:
        print(f"\nAlso checking today's date: {today}")
        check_inward_transactions(today)
