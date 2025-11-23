# JWT Authentication API Documentation

## Overview
Updated authentication system with JWT tokens and standardized JSON responses.

## API Endpoints

### 1. User Registration
**URL**: `POST /api/users/register/`

**Request**:
```json
{
  "username": "string",
  "password": "string", 
  "role": "user|admin"  // Optional, defaults to "user"
}
```

**Response**:
```json
{
  "username": "string",
  "password": "[HIDDEN]",
  "role": "user|admin",
  "token": "jwt_token_string",
  "message": "User registered successfully."
}
```

### 2. User Login
**URL**: `POST /api/users/login/`

**Request**:
```json
{
  "username": "string",
  "password": "string"
}
```

**Response**:
```json
{
  "username": "string", 
  "password": "[HIDDEN]",
  "role": "user|admin",
  "token": "jwt_token_string",
  "message": "Login successful."
}
```

## JWT Token Usage

### Authorization Header
Include JWT token in requests:
```
Authorization: Bearer <jwt_token>
```

### Token Payload
```json
{
  "username": "string",
  "role": "user|admin", 
  "exp": timestamp,
  "iat": timestamp
}
```

## Protected Endpoints

### Using JWT Decorator
```python
from users.decorators import jwt_required, admin_required

@jwt_required
def protected_view(request):
    username = request.user_data['username']
    role = request.user_data['role']
    # Your logic here

@jwt_required
@admin_required  
def admin_only_view(request):
    # Admin only logic
```

## Example Usage

### 1. Register User
```bash
curl -X POST http://localhost:8000/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "pass123", "role": "user"}'
```

### 2. Login
```bash
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "pass123"}'
```

### 3. Use Token
```bash
curl -X GET http://localhost:8000/api/protected-endpoint/ \
  -H "Authorization: Bearer <your_jwt_token>"
```

## Security Features

- **Password Hashing**: SHA256 hashing for passwords
- **Token Expiration**: 24-hour token validity
- **Role-based Access**: Admin/user role separation
- **Signature Verification**: HMAC-SHA256 token signing
- **No External Dependencies**: Custom JWT implementation

## Migration Notes

- Admin password no longer hardcoded
- All authentication goes through DynamoDB
- JWT tokens replace session-based auth
- Standardized JSON response format
- Role-based access control ready