# JWT Protected Endpoints

## All Production API endpoints now require JWT authentication

### Headers Required:
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

### Updated Request Format:
Remove `username` from request body - it's now extracted from JWT token.

**Before:**
```json
{
  "product_id": "123",
  "username": "john",
  "quantity": 10
}
```

**After:**
```json
{
  "product_id": "123", 
  "quantity": 10
}
```

### Protected Endpoints:

#### JWT Required (All Users):
- `POST /api/production/create/`
- `POST /api/production/update/`
- `POST /api/production/alter/`
- `POST /api/production/update-details/`
- `GET /api/production/list/`
- `POST /api/production/push/`
- `POST /api/production/undo/`
- `POST /api/production/daily/`
- `POST /api/production/weekly/`
- `POST /api/production/monthly/`

#### Admin Only:
- `POST /api/production/delete/`
- `POST /api/production/delete-push/`

### Usage:
1. Login to get JWT token
2. Include token in Authorization header
3. Username automatically extracted from token
4. Role-based access enforced