#!/usr/bin/env python3
"""
Performance optimization script for the backend API
"""

import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def create_gsi_indexes():
    """Create Global Secondary Indexes for better query performance"""
    
    client = boto3.client(
        'dynamodb',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name=os.environ.get('AWS_REGION', 'ap-south-1')
    )
    
    # Create date index for stock_transactions
    try:
        client.update_table(
            TableName='stock_transactions',
            AttributeDefinitions=[
                {'AttributeName': 'date', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexUpdates=[
                {
                    'Create': {
                        'IndexName': 'DateIndex',
                        'KeySchema': [
                            {'AttributeName': 'date', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 10,
                            'WriteCapacityUnits': 5
                        }
                    }
                }
            ]
        )
        print("✅ Created DateIndex for stock_transactions")
    except Exception as e:
        print(f"DateIndex already exists or error: {e}")

if __name__ == "__main__":
    print("🚀 Optimizing API Performance...")
    create_gsi_indexes()
    print("✅ Performance optimization complete!")