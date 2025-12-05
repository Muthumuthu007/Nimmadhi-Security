#!/usr/bin/env python3
"""
Test script to check consumption report with current data in ap-south-1
"""
import boto3
from datetime import datetime

def test_consumption_report():
    dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
    table = dynamodb.Table('stock_transactions')
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"Testing Consumption Report for {today}")
    print("=" * 60)
    
    # Query today's transactions
    response = table.scan(
        FilterExpression='#d = :date',
        ExpressionAttributeNames={'#d': 'date'},
        ExpressionAttributeValues={':date': today}
    )
    
    transactions = response['Items']
    print(f"\nTotal transactions today: {len(transactions)}")
    
    # Extract consumption
    consumption_count = 0
    for tx in transactions:
        op = tx.get('operation_type')
        if op == 'PushToProduction':
            consumption_count += 1
            details = tx.get('details', {})
            print(f"\n✓ Found PushToProduction:")
            print(f"  Product: {details.get('product_name')}")
            print(f"  Deductions: {details.get('deductions', {})}")
        elif op == 'AddDefectiveGoods':
            consumption_count += 1
            details = tx.get('details', {})
            print(f"\n✓ Found AddDefectiveGoods:")
            print(f"  Item: {details.get('item_id')}")
            print(f"  Quantity: {details.get('defective_added')}")
    
    if consumption_count == 0:
        print("\n⚠ No consumption transactions found!")
        print("\nTo see data in consumption report:")
        print("1. Restart Django server: python manage.py runserver")
        print("2. Push a product to production")
        print("3. Check consumption report again")
    else:
        print(f"\n✓ Found {consumption_count} consumption transactions")
        print("Consumption report should show data!")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    test_consumption_report()
