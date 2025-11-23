#!/usr/bin/env python3
"""
Script to create GSI for GRN table transport filtering
"""
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def create_grn_transport_gsi():
    """Create transport-index GSI for GRN table"""
    try:
        dynamodb = boto3.client(
            'dynamodb',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_REGION', 'us-east-2')
        )
        
        table_name = 'grn_table'
        
        # Create GSI
        response = dynamodb.update_table(
            TableName=table_name,
            AttributeDefinitions=[
                {
                    'AttributeName': 'transport',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'date',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexUpdates=[
                {
                    'Create': {
                        'IndexName': 'transport-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'transport',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'date',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        }
                    }
                }
            ]
        )
        
        print(f"GSI 'transport-index' creation initiated for table '{table_name}'")
        print("Waiting for GSI to become active...")
        
        # Wait for GSI to be active
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        print("GSI 'transport-index' created successfully!")
        
    except Exception as e:
        if "already exists" in str(e):
            print("GSI 'transport-index' already exists")
        else:
            print(f"Error creating GSI: {e}")
            raise

if __name__ == "__main__":
    create_grn_transport_gsi()