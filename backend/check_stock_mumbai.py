import boto3

# Mumbai region
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
table = dynamodb.Table('stock')

item_id = ' Rod 10mm'

try:
    response = table.get_item(Key={'item_id': item_id})
    
    if 'Item' in response:
        print(f"✓ Found in Mumbai: '{item_id}'")
        print(f"Quantity: {response['Item'].get('quantity')}")
        print(f"GST: {response['Item'].get('gst')}")
        print(f"Total Cost: {response['Item'].get('total_cost')}")
    else:
        print(f"✗ NOT in Mumbai region")
        
except Exception as e:
    print(f"Error: {e}")
