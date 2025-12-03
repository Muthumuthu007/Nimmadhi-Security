# JWT Authentication Configuration Summary

## ✅ Configuration Complete

All API endpoints are now protected with JWT authentication except for login and register endpoints.

## Authentication Flow

1. **Register/Login** → Get JWT token
2. **Include token in requests** → `Authorization: Bearer <token>`
3. **Token expires after 6 hours** (configurable in jwt_utils.py)

## Public Endpoints (No JWT Required)

- `POST /api/users/register/` - Register new user
- `POST /api/users/login/` - Login and get JWT token

## Protected Endpoints (JWT Required)

### Stock Module
- All group operations (create, list, delete)
- All stock operations (create, update, delete, get)
- Stock quantity operations (add, subtract)
- Defective goods operations
- Stock descriptions
- Opening/closing stock
- All product operations

### Production Module
- Create, update, delete products
- Alter product components
- Push to production
- Undo production
- Get production reports (daily, weekly, monthly)

### Casting Module
- Create casting products
- Move to production
- Delete casting products
- Get all casting products

### Reports Module
- Daily/weekly/monthly consumption summaries
- Daily/weekly/monthly inward reports
- Stock transactions
- Today's logs
- Item history
- Monthly inward/outward grids
- Production summaries

### Freight Module
- Create, get, update, delete freight notes
- List freight notes

### GRN Module
- Create, get, delete GRN records
- Get GRN by transport/supplier
- List all GRN records

### Users Module
- Logout (requires JWT)
- Admin operations (view/update users)

## Admin-Only Endpoints

These require both JWT and admin role:
- `POST /api/stock/delete-transaction-data/` - Delete all transaction data
- `DELETE /api/production/delete-product/` - Delete product
- `DELETE /api/production/delete-push-to-production/` - Delete production push

## Usage Example

```bash
# 1. Login to get token
curl -X POST http://your-api/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "user1", "password": "pass123"}'

# Response: {"token": "eyJ0eXAiOiJKV1QiLCJhbGc...", ...}

# 2. Use token in subsequent requests
curl -X GET http://your-api/api/stock/get-all-stocks/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

## Error Responses

- **401 Unauthorized**: Missing or invalid token
- **403 Forbidden**: Valid token but insufficient permissions (admin required)

## Token Configuration

Located in `users/jwt_utils.py`:
- **Secret Key**: JWT_SECRET (set in Django settings)
- **Expiration**: 6 hours (JWT_EXPIRATION_HOURS)
- **Algorithm**: HMAC-SHA256

## Security Features

1. **Token Blacklisting**: Logout invalidates tokens
2. **Role-Based Access**: Admin vs User roles
3. **Token Expiration**: Automatic expiry after 6 hours
4. **Secure Hashing**: SHA-256 for signatures

## Next Steps

1. Set `JWT_SECRET` in your Django settings or environment variables
2. Update frontend to include Authorization header in all API calls
3. Implement token refresh mechanism if needed
4. Consider reducing token expiration time for production
