#!/usr/bin/env python3
"""
Test GST functionality in Stock API
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8888"

def test_create_stock_with_gst():
    """Test creating stock with GST"""
    url = f"{BASE_URL}/api/stock/create/"
    
    payload = {
        "name": "Steel Rod 12mm",
        "quantity": 100,
        "defective": 5,
        "cost_per_unit": 50.0,
        "gst": 18.0,  # 18% GST
        "stock_limit": 20,
        "username": "admin",
        "unit": "pieces",
        "group_id": "group123"
    }
    
    print("=== Testing Create Stock with GST ===")
    print(f"Request: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n=== GST Calculation Verification ===")
            print(f"Available Quantity: {data.get('quantity')}")
            print(f"Cost per Unit: {data.get('cost_per_unit')}")
            print(f"GST %: {data.get('gst')}")
            print(f"GST Amount: {data.get('gst_amount')}")
            print(f"Total Cost: {data.get('total_cost')}")
            
            # Manual calculation
            available_qty = data.get('quantity', 0)
            cost_per_unit = data.get('cost_per_unit', 0)
            gst_percent = data.get('gst', 0)
            
            base_cost = available_qty * cost_per_unit
            expected_gst = (base_cost * gst_percent) / 100
            expected_total = base_cost + expected_gst
            
            print(f"\nExpected Calculation:")
            print(f"Base Cost: {available_qty} × {cost_per_unit} = {base_cost}")
            print(f"GST Amount: ({base_cost} × {gst_percent}) / 100 = {expected_gst}")
            print(f"Total Cost: {base_cost} + {expected_gst} = {expected_total}")
            
    except Exception as e:
        print(f"Error: {e}")

def test_add_stock_with_gst():
    """Test adding stock quantity with GST calculation"""
    url = f"{BASE_URL}/api/stock/add-quantity/"
    
    payload = {
        "name": "Steel Rod 12mm",
        "quantity_to_add": 50,
        "username": "admin",
        "supplier_name": "ABC Steel Ltd"
    }
    
    print("\n=== Testing Add Stock Quantity with GST ===")
    print(f"Request: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n=== GST Calculation for Added Stock ===")
            print(f"Quantity Added: {data.get('quantity_added')}")
            print(f"GST %: {data.get('gst')}")
            print(f"GST Amount: {data.get('gst_amount')}")
            print(f"Added Cost (including GST): {data.get('added_cost')}")
            print(f"New Total Cost: {data.get('new_total_cost')}")
            
    except Exception as e:
        print(f"Error: {e}")

def test_get_stock_with_gst():
    """Test getting stock data to verify GST fields"""
    url = f"{BASE_URL}/api/stock/list/"
    
    print("\n=== Testing Get Stock Data with GST ===")
    
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            stocks = response.json()
            for stock in stocks:
                if stock.get('item_id') == 'Steel Rod 12mm':
                    print(f"Stock Data: {json.dumps(stock, indent=2)}")
                    break
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("GST Functionality Test Suite")
    print("=" * 50)
    
    # Test sequence
    test_create_stock_with_gst()
    test_add_stock_with_gst()
    test_get_stock_with_gst()
    
    print("\n" + "=" * 50)
    print("Test completed!")