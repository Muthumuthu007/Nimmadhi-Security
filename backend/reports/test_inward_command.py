"""
Test script for InwardService functionality
Run with: python manage.py shell < reports/test_inward_command.py
"""
from datetime import datetime, timedelta
import json
from reports.inward_service import InwardService

def test_daily_inward():
    """Test daily inward functionality"""
    print("Testing daily inward service...")
    
    try:
        # Test with current IST date
        ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        test_date = ist_now.strftime('%Y-%m-%d')
        
        result = InwardService.get_daily_inward(test_date)
        
        print("✓ Daily inward service executed successfully")
        print(f"Report period: {result['report_period']}")
        
        inward_data = result.get('inward', {})
        if inward_data:
            print(f"Found inward data for {len(inward_data)} dates")
            for date_str, date_data in inward_data.items():
                print(f"  Date {date_str}: {len(date_data)} groups")
        else:
            print("No inward data found")
            
        return result
        
    except Exception as e:
        print(f"Daily inward test failed: {str(e)}")
        return None

def test_weekly_inward():
    """Test weekly inward functionality"""
    print("\nTesting weekly inward service...")
    
    try:
        # Test with current week
        ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        end_date = ist_now.strftime('%Y-%m-%d')
        start_date = (ist_now - timedelta(days=7)).strftime('%Y-%m-%d')
        
        result = InwardService.get_weekly_inward(start_date, end_date)
        
        print("✓ Weekly inward service executed successfully")
        print(f"Report period: {result['report_period']}")
        print(f"Total quantity: {result.get('total_inward_quantity', 0)}")
        print(f"Total amount: {result.get('total_inward_amount', 0)}")
        
        return result
        
    except Exception as e:
        print(f"Weekly inward test failed: {str(e)}")
        return None

def show_sample_data_structure():
    """Show expected data structure"""
    print("\nExpected DynamoDB data structure:")
    print("1. stock_transactions table:")
    sample_txn = {
        "operation_type": "AddStockQuantity",
        "date": "2024-01-15",
        "details": {
            "item_id": "item_001",
            "quantity_added": 100.0,
            "new_available": 150.0,
            "added_cost": 5000.0
        }
    }
    print(json.dumps(sample_txn, indent=2))
    
    print("\n2. stock table:")
    sample_stock = {
        "item_id": "item_001",
        "name": "Steel Rods",
        "group_id": "group_001"
    }
    print(json.dumps(sample_stock, indent=2))
    
    print("\n3. Groups table:")
    sample_group = {
        "group_id": "group_001",
        "name": "Construction Materials",
        "parent_id": None
    }
    print(json.dumps(sample_group, indent=2))

# Run tests
if __name__ == "__main__":
    print("=" * 60)
    print("INWARD SERVICE TEST SUITE")
    print("=" * 60)
    
    # Test daily inward
    daily_result = test_daily_inward()
    
    # Test weekly inward
    weekly_result = test_weekly_inward()
    
    # Show sample data structure
    show_sample_data_structure()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)