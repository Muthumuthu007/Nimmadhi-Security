#!/usr/bin/env python3
"""
Check all transactions for today
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.dynamodb_service import dynamodb_service
from datetime import datetime

today = datetime.now().strftime("%Y-%m-%d")
print(f"\n{'='*60}")
print(f"All Transactions for: {today}")
print(f"{'='*60}\n")

# Get all transactions for today
all_txns = dynamodb_service.scan_table('stock_transactions')
today_txns = [tx for tx in all_txns if tx.get('date') == today]

print(f"Total transactions today: {len(today_txns)}\n")

if today_txns:
    for i, tx in enumerate(today_txns, 1):
        print(f"{i}. {tx.get('operation_type')} at {tx.get('timestamp')}")
        details = tx.get('details', {})
        print(f"   Item: {details.get('item_id')}")
        if tx.get('operation_type') == 'AddStockQuantity':
            print(f"   Qty Added: {details.get('quantity_added')}")
            print(f"   GST %: {details.get('gst_percentage')}")
            print(f"   GST Amount: {details.get('gst_amount')}")
            print(f"   Added Cost: {details.get('added_cost')}")
        print()
else:
    print("❌ No transactions found for today")
    print("\nMost recent transactions:")
    sorted_txns = sorted(all_txns, key=lambda x: x.get('timestamp', ''), reverse=True)[:5]
    for tx in sorted_txns:
        print(f"  - {tx.get('date')} {tx.get('timestamp')} | {tx.get('operation_type')} | {tx.get('details', {}).get('item_id')}")
