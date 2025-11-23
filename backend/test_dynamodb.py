#!/usr/bin/env python
import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.dynamodb_service import dynamodb_service
from botocore.exceptions import ClientError

def test_dynamodb_connection():
    try:
        print("Testing DynamoDB connection...")
        
        # Test connection by listing tables
        import boto3
        from django.conf import settings
        
        dynamodb = boto3.client(
            'dynamodb',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        # List all tables
        response = dynamodb.list_tables()
        print(f"Available tables: {response['TableNames']}")
        
        # Test specific table access
        try:
            users_table = dynamodb_service.get_table('USERS')
            print(f"Users table found: {users_table.table_name}")
            
            # Try to scan the table (just to test access)
            response = users_table.scan(Limit=1)
            print("Successfully accessed Users table")
            
        except Exception as e:
            print(f"Error accessing Users table: {e}")
            
    except Exception as e:
        print(f"DynamoDB connection error: {e}")

if __name__ == "__main__":
    test_dynamodb_connection()