#!/usr/bin/env python3
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def create_casting_products_table():
    dynamodb = boto3.resource(
        'dynamodb',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name=os.environ.get('AWS_REGION', 'us-east-2')
    )
    
    table_name = 'casting_products'
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'product_id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'product_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        print(f"Creating table {table_name}...")
        table.wait_until_exists()
        print(f"Table {table_name} created successfully!")
        
    except Exception as e:
        if 'ResourceInUseException' in str(e):
            print(f"Table {table_name} already exists")
        else:
            print(f"Error creating table: {e}")

if __name__ == "__main__":
    create_casting_products_table()