#!/usr/bin/env python3
"""
Test script to verify user role functionality
"""
import os
import sys
import django
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
sys.path.append(str(backend_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.dynamodb_service import dynamodb_service
from users.utils import get_user_role, is_admin

def test_user_roles():
    """Test user role functionality"""
    print("Testing user roles...")
    
    # Get all users and display their roles
    users = dynamodb_service.scan_table('USERS')
    print(f"\nFound {len(users)} users:")
    
    for user in users:
        username = user['username']
        role = user.get('role', 'No role')
        admin_status = is_admin(username)
        print(f"  {username}: {role} (Admin: {admin_status})")
    
    # Test utility functions
    print(f"\nTesting utility functions:")
    print(f"get_user_role('admin'): {get_user_role('admin')}")
    print(f"is_admin('admin'): {is_admin('admin')}")
    print(f"get_user_role('muthu'): {get_user_role('muthu')}")
    print(f"is_admin('muthu'): {is_admin('muthu')}")

if __name__ == "__main__":
    test_user_roles()