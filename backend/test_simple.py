#!/usr/bin/env python
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from production.models import Product, PushToProduction
from stock.models import Stock, Group
import uuid

def test_direct_creation():
    """Test creating production records directly"""
    print("Testing direct model creation...")
    
    # Create a simple push record
    push_id = str(uuid.uuid4())
    push = PushToProduction.objects.create(
        push_id=push_id,
        product_id="test_product",
        product_name="Test Product",
        quantity_produced=10,
        stock_deductions={},
        username="testuser",
        production_cost_per_unit=100.0,
        total_production_cost=1000.0
    )
    
    print(f"Created push record: {push.push_id}")
    
    # Query it back
    records = list(PushToProduction.objects.all().values())
    print(f"All records: {records}")
    
    # Test daily query
    from datetime import datetime
    today = datetime.now().date()
    daily_records = list(PushToProduction.objects.filter(timestamp__date=today).values())
    print(f"Today's records: {daily_records}")

if __name__ == "__main__":
    test_direct_creation()