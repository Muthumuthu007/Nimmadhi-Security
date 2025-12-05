#!/usr/bin/env python3
"""
Test daily normal report for today
"""
import os
import sys
import django
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from datetime import datetime
from reports.normal_reports import compute_item_rows_and_totals

today = datetime.now().strftime("%Y-%m-%d")
print(f"\n{'='*70}")
print(f"Testing Daily Normal Report for: {today}")
print(f"{'='*70}\n")

try:
    rows, totals = compute_item_rows_and_totals(today, today)
    
    print(f"Total items in report: {len(rows)}")
    print(f"\nReport Totals:")
    print(f"  - Total Opening Stock Qty: {totals['total_opening_stock_qty']}")
    print(f"  - Total Inward Qty: {totals['total_inward_qty']}")
    print(f"  - Total Consumption Qty: {totals['total_consumption_qty']}")
    print(f"  - Total Balance Qty: {totals['total_balance_qty']}")
    
    # Show items with inward quantity
    items_with_inward = [r for r in rows if r['inward_qty'] > 0]
    
    if items_with_inward:
        print(f"\n✅ Items with Inward Quantity ({len(items_with_inward)} items):")
        for item in items_with_inward[:10]:  # Show first 10
            print(f"  - {item['description']}: Inward Qty = {item['inward_qty']}, Amount = {item['inward_amount']}")
    else:
        print(f"\n❌ No items with inward quantity for {today}")
        print(f"\nShowing sample items (first 5):")
        for item in rows[:5]:
            print(f"  - {item['description']}: Inward Qty = {item['inward_qty']}")
    
    print(f"\n{'='*70}\n")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
