#!/usr/bin/env python3
"""
Test script for Casting Product APIs
"""
import json
import requests

BASE_URL = "http://localhost:8000/api/lambda/"

def test_create_casting_product():
    """Test CreateCastingProduct API"""
    payload = {
        "operation": "CreateCastingProduct",
        "product_name": "Test Casting Product",
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
    
    response = requests.post(BASE_URL, json=payload)
    print(f"CreateCastingProduct Response: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    
    if response.status_code == 200:
        return response.json().get("product_id")
    return None

def test_move_to_production(product_id):
    """Test MoveToProduction API"""
    payload = {
        "operation": "MoveToProduction",
        "product_id": product_id,
        "username": "testuser"
    }
    
    response = requests.post(BASE_URL, json=payload)
    print(f"MoveToProduction Response: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

def test_delete_casting_product(product_id):
    """Test DeleteCastingProduct API"""
    payload = {
        "operation": "DeleteCastingProduct",
        "product_id": product_id,
        "username": "testuser"
    }
    
    response = requests.post(BASE_URL, json=payload)
    print(f"DeleteCastingProduct Response: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    print("Testing Casting Product APIs...")
    
    # Test 1: Create casting product
    print("\n1. Testing CreateCastingProduct...")
    product_id = test_create_casting_product()
    
    if product_id:
        # Test 2: Delete casting product
        print(f"\n2. Testing DeleteCastingProduct with ID: {product_id}...")
        test_delete_casting_product(product_id)
        
        # Test 3: Create another for move to production test
        print("\n3. Creating another casting product for MoveToProduction test...")
        product_id2 = test_create_casting_product()
        
        if product_id2:
            print(f"\n4. Testing MoveToProduction with ID: {product_id2}...")
            test_move_to_production(product_id2)
    
    print("\nTesting completed!")