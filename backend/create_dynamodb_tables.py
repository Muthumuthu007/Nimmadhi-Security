#!/usr/bin/env python3
import boto3
from botocore.exceptions import ClientError

# AWS credentials
AWS_ACCESS_KEY_ID = "AKIARZ5BM72IPMACMEYR"
AWS_SECRET_ACCESS_KEY = "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"
AWS_REGION = "us-east-2"

# Initialize DynamoDB client
dynamodb = boto3.client(
    'dynamodb',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def create_table(table_name, key_schema, attribute_definitions):
    """Create a DynamoDB table"""
    try:
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"✅ Creating table: {table_name}")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"✅ Table {table_name} already exists")
            return True
        else:
            print(f"❌ Error creating table {table_name}: {e}")
            return False

def main():
    print("🚀 Creating DynamoDB tables for Django Casting API...")
    print(f"Region: {AWS_REGION}")
    print("-" * 50)
    
    tables_to_create = [
        {
            'name': 'users',
            'key_schema': [{'AttributeName': 'username', 'KeyType': 'HASH'}],
            'attributes': [{'AttributeName': 'username', 'AttributeType': 'S'}]
        },
        {
            'name': 'casting_products',
            'key_schema': [{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            'attributes': [{'AttributeName': 'product_id', 'AttributeType': 'S'}]
        },
        {
            'name': 'production',
            'key_schema': [{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            'attributes': [{'AttributeName': 'product_id', 'AttributeType': 'S'}]
        },
        {
            'name': 'stock',
            'key_schema': [{'AttributeName': 'item_id', 'KeyType': 'HASH'}],
            'attributes': [{'AttributeName': 'item_id', 'AttributeType': 'S'}]
        },
        {
            'name': 'transactions',
            'key_schema': [{'AttributeName': 'transaction_id', 'KeyType': 'HASH'}],
            'attributes': [{'AttributeName': 'transaction_id', 'AttributeType': 'S'}]
        },
        {
            'name': 'undo_actions',
            'key_schema': [{'AttributeName': 'action_id', 'KeyType': 'HASH'}],
            'attributes': [{'AttributeName': 'action_id', 'AttributeType': 'S'}]
        },
        {
            'name': 'push_to_production',
            'key_schema': [{'AttributeName': 'push_id', 'KeyType': 'HASH'}],
            'attributes': [{'AttributeName': 'push_id', 'AttributeType': 'S'}]
        },
        {
            'name': 'grn_table',
            'key_schema': [{'AttributeName': 'grn_id', 'KeyType': 'HASH'}],
            'attributes': [{'AttributeName': 'grn_id', 'AttributeType': 'S'}]
        }
    ]
    
    success_count = 0
    for table_config in tables_to_create:
        if create_table(
            table_config['name'],
            table_config['key_schema'],
            table_config['attributes']
        ):
            success_count += 1
    
    print("-" * 50)
    print(f"✅ Successfully created/verified {success_count}/{len(tables_to_create)} tables")
    
    if success_count == len(tables_to_create):
        print("🎉 All DynamoDB tables are ready!")
        print("Your Django application should now work properly.")
    else:
        print("⚠️ Some tables failed to create. Check the errors above.")

if __name__ == "__main__":
    main()