#!/usr/bin/env python3
"""
Test JWT authentication functionality
"""
import os
import sys
import django
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
sys.path.append(str(backend_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

try:
    from users.jwt_utils import generate_jwt_token, decode_jwt_token
    
    # Test JWT functionality
    print("Testing JWT functionality...")
    
    # Generate token
    token = generate_jwt_token('testuser', 'admin')
    print(f"Generated token: {token[:50]}...")
    
    # Decode token
    payload = decode_jwt_token(token)
    print(f"Decoded payload: {payload}")
    
    print("✅ JWT functionality working")
    
except ImportError as e:
    print(f"❌ PyJWT not installed: {e}")
    print("Please install PyJWT: pip install PyJWT==2.8.0")
except Exception as e:
    print(f"❌ Error: {e}")