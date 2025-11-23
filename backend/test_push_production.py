#!/usr/bin/env python
"""
Simple test script to verify push to production functionality
"""
import os
import sys
import django
import json
import requests

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

def test_push_to_production():
    """Test the push to production endpoint directly"""
    
    # Test payload matching the lambda function structure
    payload = {
        "product_id": "test-product-123",
        "quantity": 5,
        "username": "testuser"
    }
    
    print("Testing push to production with payload:")
    print(json.dumps(payload, indent=2))
    
    try:
        # Test via Django test client
        from django.test import Client
        client = Client()
        
        response = client.post(
            '/api/production/push/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Content: {response.content.decode()}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Push to production successful!")
            print(f"Push ID: {result.get('push_id')}")
            print(f"Product: {result.get('product_name')}")
            print(f"Quantity: {result.get('quantity_produced')}")
        else:
            print(f"\n❌ Push to production failed: {response.content.decode()}")
            
    except Exception as e:
        print(f"\n❌ Error testing push to production: {e}")

if __name__ == "__main__":
    test_push_to_production()