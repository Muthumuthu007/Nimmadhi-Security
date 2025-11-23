#!/usr/bin/env python3
"""
Script to create GRN DynamoDB table
"""
import boto3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_grn_table():
    """Create the GRN DynamoDB table"""
    try:
        # Initialize DynamoDB client
        dynamodb = boto3.client(
            'dynamodb',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_REGION', 'us-east-2')
        )
        
        # Table definition
        table_name = 'grn_table'
        
        # Check if table already exists
        try:
            response = dynamodb.describe_table(TableName=table_name)
            print(f"Table '{table_name}' already exists")
            return
        except dynamodb.exceptions.ResourceNotFoundException:
            pass
        
        # Create table
        table_definition = {
            'TableName': table_name,
            'KeySchema': [
                {
                    'AttributeName': 'grnId',
                    'KeyType': 'HASH'  # Primary key
                }
            ],
            'AttributeDefinitions': [
                {
                    'AttributeName': 'grnId',
                    'AttributeType': 'S'  # String
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST'  # On-demand billing
        }
        
        print(f"Creating table '{table_name}'...")
        response = dynamodb.create_table(**table_definition)
        
        # Wait for table to be created
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        print(f"Table '{table_name}' created successfully!")
        print(f"Table ARN: {response['TableDescription']['TableArn']}")
        
    except Exception as e:
        print(f"Error creating table: {e}")
        raise

if __name__ == "__main__":
    create_grn_table()