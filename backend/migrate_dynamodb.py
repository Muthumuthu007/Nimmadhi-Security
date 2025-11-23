#!/usr/bin/env python3
"""
Migrate data from DynamoDB to Django models
"""
import os
import django
import boto3
import json
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from users.models import User, Group
from stock.models import Stock, StockRemarks
from production.models import Product, PushToProduction
from undo.models import StockTransaction, UndoAction

# DynamoDB setup
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')

def convert_decimal(obj):
    """Convert DynamoDB Decimal to Python types"""
    if isinstance(obj, list):
        return [convert_decimal(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj

def migrate_users():
    """Migrate users table"""
    print("Migrating users...")
    table = dynamodb.Table('users')
    response = table.scan()
    
    for item in response['Items']:
        item = convert_decimal(item)
        User.objects.get_or_create(
            username=item['username'],
            defaults={'password': item.get('password', '')}
        )
    print(f"Migrated {len(response['Items'])} users")

def migrate_groups():
    """Migrate Groups table"""
    print("Migrating groups...")
    table = dynamodb.Table('Groups')
    response = table.scan()
    
    for item in response['Items']:
        item = convert_decimal(item)
        Group.objects.get_or_create(
            group_id=item['group_id'],
            defaults={
                'name': item['name'],
                'parent_id': item.get('parent_id')
            }
        )
    print(f"Migrated {len(response['Items'])} groups")

def migrate_stock():
    """Migrate stock table"""
    print("Migrating stock...")
    table = dynamodb.Table('stock')
    response = table.scan()
    
    for item in response['Items']:
        item = convert_decimal(item)
        Stock.objects.get_or_create(
            item_id=item['item_id'],
            defaults={
                'name': item.get('name', item['item_id']),
                'quantity': item.get('quantity', 0),
                'cost_per_unit': item.get('cost_per_unit', 0),
                'total_cost': item.get('total_cost', 0),
                'stock_limit': item.get('stock_limit', 0),
                'defective': item.get('defective', 0),
                'total_quantity': item.get('total_quantity', 0),
                'unit': item.get('unit', ''),
                'username': item.get('username', ''),
                'group_id': item.get('group_id')
            }
        )
    print(f"Migrated {len(response['Items'])} stock items")

def migrate_stock_remarks():
    """Migrate stock_remarks table"""
    print("Migrating stock remarks...")
    try:
        table = dynamodb.Table('stock_remarks')
        response = table.scan()
        
        for item in response['Items']:
            item = convert_decimal(item)
            StockRemarks.objects.get_or_create(
                stock=item['stock'],
                defaults={
                    'description': item.get('description', ''),
                    'username': item.get('username', ''),
                    'created_at': item.get('created_at')
                }
            )
        print(f"Migrated {len(response['Items'])} stock remarks")
    except Exception as e:
        print(f"Stock remarks migration failed: {e}")

def migrate_production():
    """Migrate production table"""
    print("Migrating products...")
    table = dynamodb.Table('production')
    response = table.scan()
    
    for item in response['Items']:
        item = convert_decimal(item)
        Product.objects.get_or_create(
            product_id=item['product_id'],
            defaults={
                'product_name': item.get('product_name', ''),
                'stock_needed': item.get('stock_needed', {}),
                'max_produce': item.get('max_produce', 0),
                'original_max_produce': item.get('original_max_produce', 0),
                'username': item.get('username', ''),
                'production_cost_breakdown': item.get('production_cost_breakdown', {}),
                'production_cost_total': item.get('production_cost_total', 0),
                'wastage_percent': item.get('wastage_percent', 0),
                'wastage_amount': item.get('wastage_amount', 0),
                'transport_cost': item.get('transport_cost', 0),
                'labour_cost': item.get('labour_cost', 0),
                'other_cost': item.get('other_cost', 0),
                'total_cost': item.get('total_cost', 0),
                'inventory': item.get('inventory', 0)
            }
        )
    print(f"Migrated {len(response['Items'])} products")

def migrate_push_to_production():
    """Migrate push_to_production table"""
    print("Migrating push to production...")
    table = dynamodb.Table('push_to_production')
    response = table.scan()
    
    for item in response['Items']:
        item = convert_decimal(item)
        PushToProduction.objects.get_or_create(
            push_id=item['push_id'],
            defaults={
                'product_id': item.get('product_id', ''),
                'product_name': item.get('product_name', ''),
                'quantity_produced': item.get('quantity_produced', 0),
                'stock_deductions': item.get('stock_deductions', {}),
                'status': item.get('status', 'ACTIVE'),
                'username': item.get('username', ''),
                'production_cost_per_unit': item.get('production_cost_per_unit', 0),
                'total_production_cost': item.get('total_production_cost', 0)
            }
        )
    print(f"Migrated {len(response['Items'])} push records")

def migrate_transactions():
    """Migrate stock_transactions table"""
    print("Migrating transactions...")
    table = dynamodb.Table('stock_transactions')
    response = table.scan()
    
    for item in response['Items']:
        item = convert_decimal(item)
        StockTransaction.objects.get_or_create(
            transaction_id=item['transaction_id'],
            defaults={
                'operation_type': item.get('operation_type', item.get('operation', '')),
                'details': item.get('details', {}),
                'date': item.get('date'),
                'timestamp': item.get('timestamp')
            }
        )
    print(f"Migrated {len(response['Items'])} transactions")

def migrate_undo_actions():
    """Migrate undo_actions table"""
    print("Migrating undo actions...")
    table = dynamodb.Table('undo_actions')
    response = table.scan()
    
    for item in response['Items']:
        item = convert_decimal(item)
        UndoAction.objects.get_or_create(
            undo_id=item['undo_id'],
            defaults={
                'operation': item.get('operation', ''),
                'undo_details': item.get('undo_details', {}),
                'username': item.get('username', ''),
                'status': item.get('status', 'ACTIVE'),
                'timestamp': item.get('timestamp')
            }
        )
    print(f"Migrated {len(response['Items'])} undo actions")

def main():
    """Run all migrations"""
    print("🚀 Starting DynamoDB → Django migration...")
    
    try:
        migrate_users()
        migrate_groups()
        migrate_stock()
        migrate_stock_remarks()
        migrate_production()
        migrate_push_to_production()
        migrate_transactions()
        migrate_undo_actions()
        
        print("\n✅ Migration completed successfully!")
        print("You can now run: python3 manage.py runserver")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("Make sure:")
        print("1. AWS credentials are configured")
        print("2. DynamoDB tables exist in us-east-2")
        print("3. Django migrations are applied")

if __name__ == "__main__":
    main()