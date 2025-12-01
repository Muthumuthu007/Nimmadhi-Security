"""
Script to create DynamoDB tables for Freight Inward Note module
"""
import boto3
from django.conf import settings
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_freight_tables():
    """Create DynamoDB tables for freight module"""
    
    # Initialize DynamoDB client
    dynamodb = boto3.client(
        'dynamodb',
        region_name=os.environ.get('AWS_REGION', 'ap-south-1'),
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
    )
    
    try:
        # Create freight_inward table
        print("Creating freight_inward table...")
        dynamodb.create_table(
            TableName='freight_inward',
            KeySchema=[
                {
                    'AttributeName': 'freight_id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'freight_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("✓ freight_inward table created successfully")
        
    except dynamodb.exceptions.ResourceInUseException:
        print("✓ freight_inward table already exists")
    except Exception as e:
        print(f"✗ Error creating freight_inward table: {e}")
    
    try:
        # Create freight_allocations table
        print("Creating freight_allocations table...")
        dynamodb.create_table(
            TableName='freight_allocations',
            KeySchema=[
                {
                    'AttributeName': 'allocation_id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'allocation_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'freight_id',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'freight_id-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'freight_id',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("✓ freight_allocations table created successfully")
        
    except dynamodb.exceptions.ResourceInUseException:
        print("✓ freight_allocations table already exists")
    except Exception as e:
        print(f"✗ Error creating freight_allocations table: {e}")
    
    print("\nFreight tables setup completed!")
    print("\nTable structure:")
    print("1. freight_inward:")
    print("   - freight_id (Primary Key)")
    print("   - transport_vendor")
    print("   - total_amount")
    print("   - date")
    print("   - created_by")
    print("   - created_at")
    print("   - updated_at")
    print("\n2. freight_allocations:")
    print("   - allocation_id (Primary Key)")
    print("   - freight_id (GSI)")
    print("   - supplier_name")
    print("   - amount")
    print("   - created_at")


if __name__ == "__main__":
    create_freight_tables()