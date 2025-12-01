#!/usr/bin/env python3
"""
Test the Daily Report API with a specific date that has AddStockQuantity operations
"""

import os
import sys
import django
import json

# Setup Django environment
sys.path.append('/Users/muthuk/Downloads/backend 11/backend 8/backend 4/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import RequestFactory
from reports.views import get_daily_consumption_summary

def test_with_specific_date():
    """Test daily report with 2025-11-28 which has AddStockQuantity operations"""
    
    print("Testing Daily Report API with date 2025-11-28...")
    
    factory = RequestFactory()
    
    request_body = {
        "operation": "GetDailyConsumptionSummary",
        "report_date": "2025-11-28"
    }
    
    request = factory.post('/reports/daily/', 
                          data=json.dumps(request_body),
                          content_type='application/json')
    
    try:
        response = get_daily_consumption_summary(request)
        
        if response.status_code == 200:
            response_data = json.loads(response.content)
            
            print(f"✅ Daily Report API responded successfully for 2025-11-28")
            print(f"📊 Report Results:")
            print(f"   - Report Date: {response_data.get('report_date')}")
            print(f"   - Total Consumption Quantity: {response_data.get('total_consumption_quantity', 0)}")
            print(f"   - Total Consumption Amount: {response_data.get('total_consumption_amount', 0)}")
            print(f"   - Total Inward Quantity: {response_data.get('total_inward_quantity', 0)} ⭐")
            print(f"   - Total Inward Amount: {response_data.get('total_inward_amount', 0)} ⭐")
            
            # Show detailed stock summary
            stock_summary = response_data.get('stock_summary', {})
            print(f"\n📋 Stock Summary Details:")
            
            total_items_with_inward = 0
            total_items_with_consumption = 0
            
            for group_name, subgroups in stock_summary.items():
                print(f"   📁 {group_name}:")
                for subgroup_name, items in subgroups.items():
                    print(f"      📂 {subgroup_name}:")
                    for item in items:
                        inward_qty = item.get('total_quantity_added', 0)
                        consumed_qty = item.get('total_quantity_consumed', 0)
                        suppliers = item.get('suppliers', [])
                        
                        if inward_qty > 0:
                            total_items_with_inward += 1
                        if consumed_qty > 0:
                            total_items_with_consumption += 1
                            
                        print(f"         📦 {item['item_id']}:")
                        print(f"            ➕ Added: {inward_qty}")
                        print(f"            ➖ Consumed: {consumed_qty}")
                        if suppliers:
                            print(f"            🏪 Suppliers: {', '.join(suppliers)}")
            
            print(f"\n📈 Summary:")
            print(f"   - Items with stock additions: {total_items_with_inward}")
            print(f"   - Items with consumption: {total_items_with_consumption}")
            
            if total_items_with_inward > 0:
                print("✅ SUCCESS: Daily report now includes stock additions from AddStockQuantity operations!")
            else:
                print("⚠️  No stock additions found for this date")
                
        else:
            print(f"❌ API returned error: {response.status_code}")
            print(f"Response: {response.content}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_with_specific_date()