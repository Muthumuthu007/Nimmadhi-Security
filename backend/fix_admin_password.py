#!/usr/bin/env python3
import os
import sys
import django
import hashlib
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
sys.path.append(str(backend_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.dynamodb_service import dynamodb_service

# Update admin user with hashed password
hashed_password = hashlib.sha256("37773".encode()).hexdigest()

try:
    dynamodb_service.put_item('USERS', {
        'username': 'admin',
        'password': hashed_password,
        'role': 'admin'
    })
    print("✅ Admin password properly hashed and stored")
except Exception as e:
    print(f"❌ Error: {e}")