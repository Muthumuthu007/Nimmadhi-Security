import boto3
import os
from decimal import Decimal

# Set AWS credentials
os.environ['AWS_REGION'] = 'ap-south-1'

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
table = dynamodb.Table('stock')

# Check for the item
item_id = ' Rod 10mm'

try:
    response = table.get_item(Key={'item_id': item_id})
    
    if 'Item' in response:
        print(f"✓ Stock item '{item_id}' EXISTS in database")
        print("\nItem details:")
        for key, value in response['Item'].items():
            print(f"  {key}: {value}")
    else:
        print(f"✗ Stock item '{item_id}' NOT FOUND in database")
        
        # List all items to see what's there
        print("\nScanning all items in stock table...")
        scan_response = table.scan(Limit=10)
        items = scan_response.get('Items', [])
        
        if items:
            print(f"\nFound {len(items)} items (showing first 10):")
            for item in items:
                print(f"  - {item.get('item_id', 'N/A')} (qty: {item.get('quantity', 0)})")
        else:
            print("No items found in stock table")
            
except Exception as e:
    print(f"Error checking database: {e}")
