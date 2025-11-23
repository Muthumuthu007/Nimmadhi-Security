#!/usr/bin/env python
import os
import sys
import django
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from stock.models import Stock, Group
from production.models import Product, PushToProduction
from users.models import User
from django.test import Client
from django.urls import reverse

def create_test_data():
    """Create sample stock and product data"""
    print("Creating test data...")
    
    # Create test group
    group, _ = Group.objects.get_or_create(
        group_id="test_group",
        defaults={
            'name': 'Test Group',
            'parent': None
        }
    )
    
    # Create test stock items
    stock1, _ = Stock.objects.get_or_create(
        item_id="item1",
        defaults={
            'name': 'Test Item 1',
            'quantity': 100,
            'defective': 0,
            'cost_per_unit': 10.0,
            'stock_limit': 20,
            'unit': 'pcs',
            'group': group,
            'username': 'testuser'
        }
    )
    
    stock2, _ = Stock.objects.get_or_create(
        item_id="item2", 
        defaults={
            'name': 'Test Item 2',
            'quantity': 50,
            'defective': 0,
            'cost_per_unit': 15.0,
            'stock_limit': 10,
            'unit': 'pcs',
            'group': group,
            'username': 'testuser'
        }
    )
    
    print(f"Created stock items: {stock1.name}, {stock2.name}")
    return stock1, stock2

def test_create_product():
    """Test creating a product"""
    print("\n=== Testing CreateProduct ===")
    
    client = Client()
    payload = {
        "operation": "CreateProduct",
        "product_name": "Test Product",
        "stock_needed": {
            "item1": 10,
            "item2": 5
        },
        "username": "testuser",
        "wastage_percent": 5.0,
        "transport_cost": 100.0,
        "labour_cost": 200.0,
        "other_cost": 50.0
    }
    
    response = client.post('/api/lambda/', 
                          data=json.dumps(payload),
                          content_type='application/json')
    
    result = response.json()
    print(f"CreateProduct Response: {result}")
    
    if 'product_id' in result:
        return result['product_id']
    return None

def test_push_to_production(product_id):
    """Test pushing product to production"""
    print(f"\n=== Testing PushToProduction with product_id: {product_id} ===")
    
    client = Client()
    payload = {
        "operation": "PushToProduction",
        "product_id": product_id,
        "quantity": 5,
        "username": "testuser"
    }
    
    response = client.post('/api/lambda/',
                          data=json.dumps(payload), 
                          content_type='application/json')
    
    result = response.json()
    print(f"PushToProduction Response: {result}")
    
    if 'push_id' in result:
        return result['push_id']
    return None

def test_get_daily_production():
    """Test getting daily production data"""
    print(f"\n=== Testing GetDailyPushToProduction ===")
    
    client = Client()
    today = datetime.now().strftime('%Y-%m-%d')
    payload = {
        "operation": "GetDailyPushToProduction",
        "date": today,
        "username": "testuser"
    }
    
    response = client.post('/api/lambda/',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    result = response.json()
    print(f"GetDailyPushToProduction Response: {json.dumps(result, indent=2)}")
    return result

def main():
    """Run all tests"""
    print("Starting Production App Tests...")
    
    # Create test data
    create_test_data()
    
    # Test create product
    product_id = test_create_product()
    if not product_id:
        print("Failed to create product, stopping tests")
        return
    
    # Test push to production
    push_id = test_push_to_production(product_id)
    if not push_id:
        print("Failed to push to production, stopping tests")
        return
    
    # Test get daily production
    daily_result = test_get_daily_production()
    
    print(f"\n=== Test Summary ===")
    print(f"Product ID: {product_id}")
    print(f"Push ID: {push_id}")
    print(f"Daily items count: {len(daily_result.get('items', []))}")
    print(f"Daily summary count: {len(daily_result.get('summary', []))}")
    
    if daily_result.get('items'):
        print("✅ Tests completed successfully - production data is visible!")
    else:
        print("❌ Tests completed but no production data found")

if __name__ == "__main__":
    main()