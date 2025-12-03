import boto3
import os

os.environ['AWS_REGION'] = 'ap-south-1'

dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
table = dynamodb.Table('stock')

item_id = ' Rod 10mm'

try:
    # Direct get without cache
    response = table.get_item(Key={'item_id': item_id})
    
    if 'Item' in response:
        print(f"✓ Stock item '{item_id}' EXISTS")
        print(f"\nQuantity: {response['Item'].get('quantity')}")
        print(f"Total Cost: {response['Item'].get('total_cost')}")
        print(f"GST: {response['Item'].get('gst')}")
    else:
        print(f"✗ Stock item '{item_id}' NOT FOUND")
        
except Exception as e:
    print(f"Error: {e}")
