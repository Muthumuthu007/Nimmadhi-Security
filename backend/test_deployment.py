#!/usr/bin/env python3
import requests
import json

# Test the deployed application
BASE_URL = "https://production-api.eba-zu3kqpzr.us-east-1.elasticbeanstalk.com"

def test_csrf_endpoint():
    """Test CSRF token endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/csrf-token/", timeout=30)
        print(f"CSRF Endpoint Status: {response.status_code}")
        if response.status_code == 200:
            print(f"CSRF Token: {response.json()}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"CSRF Test Failed: {e}")

def test_user_registration():
    """Test user registration"""
    try:
        # First get CSRF token
        csrf_response = requests.get(f"{BASE_URL}/api/csrf-token/", timeout=30)
        if csrf_response.status_code != 200:
            print("Cannot get CSRF token")
            return
        
        csrf_token = csrf_response.json()['csrfToken']
        
        # Test registration
        headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf_token
        }
        
        data = {
            'username': 'testuser123',
            'password': 'testpass123'
        }
        
        response = requests.post(f"{BASE_URL}/api/users/register/", 
                               json=data, headers=headers, timeout=30)
        
        print(f"Registration Status: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"Registration Test Failed: {e}")

if __name__ == "__main__":
    print("🧪 Testing Deployed Application...")
    print(f"URL: {BASE_URL}")
    print("-" * 50)
    
    test_csrf_endpoint()
    print("-" * 50)
    test_user_registration()