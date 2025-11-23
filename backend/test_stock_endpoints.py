#!/usr/bin/env python3
"""
Test script for stock GET endpoints
Usage: python3 test_stock_endpoints.py
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8008/api/stock"

def test_endpoint(endpoint, params=None):
    """Test a GET endpoint and print results"""
    url = f"{BASE_URL}{endpoint}"
    try:
        print(f"\n=== Testing {endpoint} ===")
        print(f"URL: {url}")
        if params:
            print(f"Params: {params}")
        
        response = requests.get(url, params=params)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Found {len(data.get('groups', data.get('stocks', data.get('inventory', []))))} items")
        else:
            print("Error occurred!")
            
    except Exception as e:
        print(f"Request failed: {e}")

def main():
    print("Testing Stock GET Endpoints...")
    
    # Test list groups
    test_endpoint("/groups/list/")
    test_endpoint("/groups/list/", {"parent_id": "some-parent-id"})
    
    # Test get all stocks
    test_endpoint("/list/")
    test_endpoint("/list/", {"group_id": "some-group-id"})
    
    # Test inventory
    test_endpoint("/inventory/")
    test_endpoint("/inventory/", {"limit": "10", "item_name": "test"})

if __name__ == "__main__":
    main()