import os
import sys
import django

sys.path.append('d:\\backend 4\\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.dynamodb_service import dynamodb_service

# Check for inward operations
transactions = dynamodb_service.scan_table('TRANSACTIONS')
inward_ops = [tx for tx in transactions if 'AddStock' in tx.get('operation_type', '')]

print(f"Found {len(inward_ops)} inward transactions")
for i, tx in enumerate(inward_ops[:3]):
    print(f"\nInward {i+1}:")
    print(f"  Date: {tx.get('date')}")
    print(f"  Operation: {tx.get('operation_type')}")
    print(f"  Details: {tx.get('details', {})}")