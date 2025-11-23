#!/usr/bin/env python
import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
sys.path.append(str(Path(__file__).resolve().parent))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

def test_aws_connection():
    try:
        from backend.dynamodb_service import dynamodb_service
        from django.conf import settings
        
        print("=== AWS Configuration Check ===")
        print(f"AWS_ACCESS_KEY_ID: {'[SET]' if settings.AWS_ACCESS_KEY_ID else '[NOT SET]'}")
        print(f"AWS_SECRET_ACCESS_KEY: {'[SET]' if settings.AWS_SECRET_ACCESS_KEY else '[NOT SET]'}")
        print(f"AWS_REGION: {settings.AWS_REGION}")
        
        print("\n=== DynamoDB Connection Test ===")
        
        # Test connection by listing tables
        dynamodb_service._initialize()
        
        # Try to access a table
        users_table = dynamodb_service.get_table('USERS')
        print(f"[SUCCESS] Connected to DynamoDB")
        print(f"[SUCCESS] Users table accessible: {users_table.table_name}")
        
        # Test a simple scan operation
        try:
            users = dynamodb_service.scan_table('USERS')
            print(f"[SUCCESS] Scanned users table: {len(users)} users found")
        except Exception as e:
            print(f"[WARNING] Could not scan users table: {e}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] AWS Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_aws_connection()