#!/usr/bin/env python3
"""
DynamoDB Migration Script: us-east-2 → ap-south-1
"""
import boto3
import json
import os
from datetime import datetime

# Configuration
SOURCE_REGION = 'us-east-2'
TARGET_REGION = 'ap-south-1'

TABLES_TO_MIGRATE = [
    'users',
    'Groups', 
    'stock',
    'transactions',
    'production',
    'undo_actions',
    'products',
    'casting_products',
    'stock_remarks',
    'stock_transactions',
    'push_to_production',
    'grn_table'
]

def backup_table(table_name, source_region):
    """Backup table data from source region"""
    print(f"Backing up table: {table_name}")
    
    dynamodb = boto3.resource('dynamodb', region_name=source_region)
    table = dynamodb.Table(table_name)
    
    try:
        # Scan all items
        response = table.scan()
        items = response['Items']
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        # Save to file
        backup_file = f"backup_{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_file, 'w') as f:
            json.dump(items, f, default=str, indent=2)
        
        print(f"✅ Backed up {len(items)} items to {backup_file}")
        return backup_file, len(items)
        
    except Exception as e:
        print(f"❌ Error backing up {table_name}: {e}")
        return None, 0

def get_table_schema(table_name, source_region):
    """Get table schema for recreation"""
    print(f"Getting schema for: {table_name}")
    
    dynamodb = boto3.client('dynamodb', region_name=source_region)
    
    try:
        response = dynamodb.describe_table(TableName=table_name)
        table_desc = response['Table']
        
        # Extract key schema info
        schema = {
            'TableName': table_name,
            'KeySchema': table_desc['KeySchema'],
            'AttributeDefinitions': table_desc['AttributeDefinitions'],
            'BillingMode': 'PAY_PER_REQUEST'  # Use on-demand billing
        }
        
        # Add GSI if exists
        if 'GlobalSecondaryIndexes' in table_desc:
            schema['GlobalSecondaryIndexes'] = []
            for gsi in table_desc['GlobalSecondaryIndexes']:
                gsi_schema = {
                    'IndexName': gsi['IndexName'],
                    'KeySchema': gsi['KeySchema'],
                    'Projection': gsi['Projection']
                }
                schema['GlobalSecondaryIndexes'].append(gsi_schema)
        
        return schema
        
    except Exception as e:
        print(f"❌ Error getting schema for {table_name}: {e}")
        return None

def create_table_in_target(schema, target_region):
    """Create table in target region"""
    table_name = schema['TableName']
    print(f"Creating table in {target_region}: {table_name}")
    
    dynamodb = boto3.client('dynamodb', region_name=target_region)
    
    try:
        # Check if table already exists
        try:
            dynamodb.describe_table(TableName=table_name)
            print(f"⚠️ Table {table_name} already exists in {target_region}")
            return True
        except dynamodb.exceptions.ResourceNotFoundException:
            pass
        
        # Create table
        response = dynamodb.create_table(**schema)
        
        # Wait for table to be active
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        print(f"✅ Created table: {table_name}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating table {table_name}: {e}")
        return False

def restore_data(backup_file, table_name, target_region):
    """Restore data to target region"""
    print(f"Restoring data to {table_name} in {target_region}")
    
    if not backup_file or not os.path.exists(backup_file):
        print(f"❌ Backup file not found: {backup_file}")
        return False
    
    dynamodb = boto3.resource('dynamodb', region_name=target_region)
    table = dynamodb.Table(table_name)
    
    try:
        # Load backup data
        with open(backup_file, 'r') as f:
            items = json.load(f)
        
        # Batch write items (25 items per batch - DynamoDB limit)
        with table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)
        
        print(f"✅ Restored {len(items)} items to {table_name}")
        return True
        
    except Exception as e:
        print(f"❌ Error restoring data to {table_name}: {e}")
        return False

def main():
    """Main migration process"""
    print("=" * 60)
    print("DYNAMODB MIGRATION: us-east-2 → ap-south-1")
    print("=" * 60)
    
    # Check AWS credentials
    try:
        boto3.client('sts').get_caller_identity()
        print("✅ AWS credentials configured")
    except Exception as e:
        print(f"❌ AWS credentials not configured: {e}")
        return
    
    migration_log = []
    
    for table_name in TABLES_TO_MIGRATE:
        print(f"\n📋 Processing table: {table_name}")
        
        # Step 1: Backup data
        backup_file, item_count = backup_table(table_name, SOURCE_REGION)
        if not backup_file:
            migration_log.append(f"❌ {table_name}: Backup failed")
            continue
        
        # Step 2: Get schema
        schema = get_table_schema(table_name, SOURCE_REGION)
        if not schema:
            migration_log.append(f"❌ {table_name}: Schema extraction failed")
            continue
        
        # Step 3: Create table in target
        if not create_table_in_target(schema, TARGET_REGION):
            migration_log.append(f"❌ {table_name}: Table creation failed")
            continue
        
        # Step 4: Restore data
        if restore_data(backup_file, table_name, TARGET_REGION):
            migration_log.append(f"✅ {table_name}: Migrated {item_count} items")
        else:
            migration_log.append(f"❌ {table_name}: Data restoration failed")
    
    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    for log in migration_log:
        print(log)
    
    print(f"\n🎯 Next step: Update AWS_REGION to '{TARGET_REGION}' in your config")

if __name__ == "__main__":
    main()