#!/usr/bin/env python3
"""
Setup script to test DynamoDB connection and create tables if needed
"""
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
import boto3
from botocore.exceptions import ClientError

def test_connection():
    """Test DynamoDB connection"""
    try:
        # Test connection by listing tables
        dynamodb = boto3.client(
            'dynamodb',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_REGION', 'us-east-2')
        )
        
        response = dynamodb.list_tables()
        print("✅ DynamoDB connection successful!")
        print(f"Available tables: {response.get('TableNames', [])}")
        return True
        
    except ClientError as e:
        print(f"❌ DynamoDB connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_table_access():
    """Test access to specific tables"""
    from django.conf import settings
    
    for table_key, table_name in settings.DYNAMODB_TABLES.items():
        try:
            table = dynamodb_service.get_table(table_key)
            # Try to scan with limit to test access
            response = table.scan(Limit=1)
            print(f"✅ {table_key} ({table_name}): Accessible")
        except ClientError as e:
            print(f"❌ {table_key} ({table_name}): {e}")
        except Exception as e:
            print(f"❌ {table_key} ({table_name}): {e}")

if __name__ == "__main__":
    print("🔧 Testing DynamoDB Setup...")
    print("=" * 50)
    
    # Check environment variables
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file or environment")
        sys.exit(1)
    
    print("✅ Environment variables found")
    
    # Test connection
    if test_connection():
        print("\n🔍 Testing table access...")
        test_table_access()
    
    print("\n" + "=" * 50)
    print("Setup test complete!")