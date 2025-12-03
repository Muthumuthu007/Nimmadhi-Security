import boto3

dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
table = dynamodb.Table('stock')

response = table.get_item(Key={'item_id': 'Example'})

if 'Item' in response:
    item = response['Item']
    print("=== STOCK ITEM: Example ===")
    print(f"Quantity: {item.get('quantity')}")
    print(f"Cost per unit: {item.get('cost_per_unit')}")
    print(f"GST %: {item.get('gst')}")
    print(f"GST Amount: {item.get('gst_amount')}")
    print(f"Total Cost: {item.get('total_cost')}")
    print(f"\nExpected: 100 * 50 = 5000 + 900 (GST) = 5900")
    print(f"Actual total_cost in DB: {item.get('total_cost')}")
else:
    print("Item 'Example' not found in database")
