#!/usr/bin/env python3
"""
Ultra-fast optimization - Redis caching + batch operations
"""

import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def create_additional_indexes():
    """Create more GSIs for ultra-fast queries"""
    
    client = boto3.client(
        'dynamodb',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name=os.environ.get('AWS_REGION', 'ap-south-1')
    )
    
    # Operation type + date composite index
    try:
        client.update_table(
            TableName='stock_transactions',
            AttributeDefinitions=[
                {'AttributeName': 'operation_type', 'AttributeType': 'S'},
                {'AttributeName': 'date', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexUpdates=[
                {
                    'Create': {
                        'IndexName': 'OpTypeDateIndex',
                        'KeySchema': [
                            {'AttributeName': 'operation_type', 'KeyType': 'HASH'},
                            {'AttributeName': 'date', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 15,
                            'WriteCapacityUnits': 5
                        }
                    }
                }
            ]
        )
        print("✅ Created OpTypeDateIndex")
    except Exception as e:
        print(f"OpTypeDateIndex: {e}")

if __name__ == "__main__":
    print("⚡ Ultra-fast optimization...")
    create_additional_indexes()
    print("🚀 Ultra-fast complete!")