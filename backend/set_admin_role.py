#!/usr/bin/env python3
import os
import sys
import django
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
sys.path.append(str(backend_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.dynamodb_service import dynamodb_service

# Create admin user with admin role
try:
    dynamodb_service.put_item('USERS', {
        'username': 'admin',
        'password': '37773',
        'role': 'admin'
    })
    print("✅ Admin user created with admin role")
except Exception as e:
    print(f"❌ Error: {e}")