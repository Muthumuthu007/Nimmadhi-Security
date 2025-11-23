#!/usr/bin/env python3
"""
Test script for get_all_stocks function
"""
import os
import sys
import django
import requests
import json

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from stock.models import Stock, Group

def create_sample_data():
    """Create sample groups and stocks for testing"""
    print("Creating sample data...")
    
    # Create sample groups
    group1 = Group.objects.create(
        group_id="group-1",
        name="Electronics"
    )
    
    group2 = Group.objects.create(
        group_id="group-2", 
        name="Components",
        parent=group1
    )
    
    # Create sample stocks
    Stock.objects.create(
        item_id="item-1",
        name="Resistor 100ohm",
        quantity=95,
        total_quantity=100,
        defective=5,
        cost_per_unit=0.50,
        total_cost=47.50,
        stock_limit=20,
        unit="pcs",
        username="testuser",
        group=group2
    )
    
    Stock.objects.create(
        item_id="item-2",
        name="LED Red 5mm",
        quantity=180,
        total_quantity=200,
        defective=20,
        cost_per_unit=0.25,
        total_cost=45.00,
        stock_limit=50,
        unit="pcs", 
        username="testuser",
        group=group2
    )
    
    print("Sample data created successfully!")

def test_get_all_stocks():
    """Test the get_all_stocks endpoint"""
    print("\nTesting get_all_stocks endpoint...")
    
    base_url = "http://127.0.0.1:8000/api/stock"
    
    # Test 1: Get all stocks
    print("\n1. Testing GET all stocks:")
    try:
        response = requests.get(f"{base_url}/list/")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data.get('stocks', []))} stocks")
            for stock in data.get('stocks', [])[:2]:  # Show first 2
                print(f"  - {stock.get('name')} (Group: {stock.get('group_name')})")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 2: Get stocks for specific group
    print("\n2. Testing GET stocks for specific group:")
    try:
        response = requests.get(f"{base_url}/list/?group_id=group-2")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data.get('stocks', []))} stocks for group-2")
            for stock in data.get('stocks', []):
                print(f"  - {stock.get('name')} (Group: {stock.get('group_name')})")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

def main():
    print("Get All Stocks Test Script")
    print("=" * 50)
    
    # Clear existing data
    print("Clearing existing data...")
    Stock.objects.all().delete()
    Group.objects.all().delete()
    
    # Create sample data
    create_sample_data()
    
    # Test the endpoint
    test_get_all_stocks()
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()