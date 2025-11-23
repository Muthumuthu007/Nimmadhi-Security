#!/usr/bin/env python3
"""
Test authentication endpoints with JWT
"""
import json
import requests
from django.test import Client
from django.test.utils import setup_test_environment, teardown_test_environment

def test_register():
    """Test user registration"""
    client = Client()
    
    data = {
        "username": "testuser123",
        "password": "testpass123",
        "role": "user"
    }
    
    response = client.post('/api/users/register/', 
                          data=json.dumps(data),
                          content_type='application/json')
    
    print(f"Register Response ({response.status_code}):")
    print(json.dumps(response.json(), indent=2))
    return response.json().get('token')

def test_login():
    """Test user login"""
    client = Client()
    
    data = {
        "username": "admin",
        "password": "37773"
    }
    
    response = client.post('/api/users/login/', 
                          data=json.dumps(data),
                          content_type='application/json')
    
    print(f"Login Response ({response.status_code}):")
    print(json.dumps(response.json(), indent=2))
    return response.json().get('token')

if __name__ == "__main__":
    setup_test_environment()
    
    print("=== Testing Registration ===")
    register_token = test_register()
    
    print("\n=== Testing Login ===")
    login_token = test_login()
    
    teardown_test_environment()