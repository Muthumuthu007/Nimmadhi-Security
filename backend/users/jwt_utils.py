import json
import base64
import hmac
import hashlib
import datetime
from django.conf import settings

JWT_SECRET = getattr(settings, 'JWT_SECRET', 'your-secret-key-change-in-production')
JWT_EXPIRATION_HOURS = 6

def generate_jwt_token(username, role):
    """Generate simple JWT-like token"""
    payload = {
        'username': username,
        'role': role,
        'exp': (datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS)).timestamp(),
        'iat': datetime.datetime.utcnow().timestamp()
    }
    
    # Simple token: base64(payload).signature
    payload_str = json.dumps(payload, sort_keys=True)
    payload_b64 = base64.b64encode(payload_str.encode()).decode()
    
    signature = hmac.new(
        JWT_SECRET.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"{payload_b64}.{signature}"

def decode_jwt_token(token):
    """Decode and validate simple JWT-like token"""
    try:
        parts = token.split('.')
        if len(parts) != 2:
            return None
        
        payload_b64, signature = parts
        
        # Verify signature
        expected_signature = hmac.new(
            JWT_SECRET.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return None
        
        # Decode payload
        payload_str = base64.b64decode(payload_b64).decode()
        payload = json.loads(payload_str)
        
        # Check expiration
        if payload.get('exp', 0) < datetime.datetime.utcnow().timestamp():
            return None
        
        return payload
    except Exception:
        return None