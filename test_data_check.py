import os
import sys
import django

# Add the backend directory to Python path
sys.path.append('d:\\backend 4\\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.dynamodb_service import dynamodb_service

# Check what transactions exist
try:
    transactions = dynamodb_service.scan_table('TRANSACTIONS')
    print(f"Total transactions: {len(transactions)}")
    
    # Show sample transactions
    for i, tx in enumerate(transactions[:5]):
        print(f"\nTransaction {i+1}:")
        print(f"  Date: {tx.get('date', 'N/A')}")
        print(f"  Operation: {tx.get('operation_type', 'N/A')}")
        print(f"  Details: {tx.get('details', {})}")
        
    # Check unique dates
    dates = set(tx.get('date') for tx in transactions if tx.get('date'))
    print(f"\nUnique dates: {sorted(dates)}")
    
    # Check operations
    ops = set(tx.get('operation_type') for tx in transactions if tx.get('operation_type'))
    print(f"\nUnique operations: {sorted(ops)}")
    
except Exception as e:
    print(f"Error: {e}")