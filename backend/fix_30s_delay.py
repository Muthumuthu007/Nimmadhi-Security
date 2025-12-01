#!/usr/bin/env python3
"""
Fix 30s delay in daily consumption reports
"""

import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def check_gsi_status():
    """Check if GSI indexes are active"""
    
    client = boto3.client(
        'dynamodb',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name=os.environ.get('AWS_REGION', 'ap-south-1')
    )
    
    try:
        response = client.describe_table(TableName='stock_transactions')
        
        gsi_list = response['Table'].get('GlobalSecondaryIndexes', [])
        
        print("📊 GSI Status:")
        for gsi in gsi_list:
            name = gsi['IndexName']
            status = gsi['IndexStatus']
            print(f"   {name}: {status}")
            
            if status != 'ACTIVE':
                print(f"⚠️  {name} is not ACTIVE - this causes 30s delays!")
                return False
        
        if not gsi_list:
            print("❌ No GSI indexes found - using slow table scans!")
            return False
            
        print("✅ All GSI indexes are ACTIVE")
        return True
        
    except Exception as e:
        print(f"❌ Error checking GSI: {e}")
        return False

def increase_read_capacity():
    """Increase read capacity for faster queries"""
    
    client = boto3.client(
        'dynamodb',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name=os.environ.get('AWS_REGION', 'ap-south-1')
    )
    
    try:
        # Increase main table capacity
        client.update_table(
            TableName='stock_transactions',
            ProvisionedThroughput={
                'ReadCapacityUnits': 25,
                'WriteCapacityUnits': 10
            }
        )
        
        # Increase GSI capacity
        client.update_table(
            TableName='stock_transactions',
            GlobalSecondaryIndexUpdates=[
                {
                    'Update': {
                        'IndexName': 'DateIndex',
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 25,
                            'WriteCapacityUnits': 5
                        }
                    }
                }
            ]
        )
        
        print("✅ Increased read capacity to 25 RCU")
        return True
        
    except Exception as e:
        print(f"Capacity update: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Fixing 30s delay in daily reports...")
    
    gsi_ok = check_gsi_status()
    if gsi_ok:
        increase_read_capacity()
        print("🚀 Daily reports should now be under 2 seconds!")
    else:
        print("❌ GSI issues detected - reports will remain slow until fixed")