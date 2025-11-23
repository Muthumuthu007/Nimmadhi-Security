#!/usr/bin/env python3
"""
Simple test for consumption summary using Django test client
"""

import os
import sys
import django
import json

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import Client
from django.urls import reverse

def test_consumption_summary():
    """Test daily consumption summary endpoint"""
    client = Client()
    
    # Test with specific date
    payload = {
        "report_date": "2024-12-01"
    }
    
    try:
        print(f"\n=== Testing Daily Consumption Summary ===")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = client.post('/api/reports/consumption/daily/', 
                             data=json.dumps(payload), 
                             content_type='application/json')
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error Response: {response.content.decode()}")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

def test_consumption_no_date():
    """Test consumption summary without date"""
    client = Client()
    
    payload = {}
    
    try:
        print(f"\n=== Testing Consumption Summary (No Date) ===")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = client.post('/api/reports/consumption/daily/', 
                             data=json.dumps(payload), 
                             content_type='application/json')
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error Response: {response.content.decode()}")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_consumption_summary()
    test_consumption_no_date()