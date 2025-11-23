#!/usr/bin/env python3
"""
Test script for consumption summary endpoint
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/reports"

def test_consumption_summary():
    """Test daily consumption summary endpoint"""
    url = f"{BASE_URL}/consumption/daily/"
    
    # Test with current date
    payload = {
        "report_date": "2024-12-01"
    }
    
    try:
        print(f"\n=== Testing Daily Consumption Summary ===")
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
    except Exception as e:
        print(f"Request failed: {e}")

def test_consumption_no_date():
    """Test consumption summary without date (should use current date)"""
    url = f"{BASE_URL}/consumption/daily/"
    
    payload = {}
    
    try:
        print(f"\n=== Testing Consumption Summary (No Date) ===")
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_consumption_summary()
    test_consumption_no_date()