import boto3

dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
table = dynamodb.Table('stock')

response = table.get_item(Key={'item_id': 'Example'})

if 'Item' in response:
    item = response['Item']
    print(f"Item: {item.get('item_id')}")
    print(f"Quantity: {item.get('quantity')}")
    print(f"Cost per unit: {item.get('cost_per_unit')}")
    print(f"GST: {item.get('gst')}")
    print(f"GST Amount: {item.get('gst_amount')}")
    print(f"Total Cost: {item.get('total_cost')}")
else:
    print("Item not found")
