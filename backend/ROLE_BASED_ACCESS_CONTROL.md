# Role-Based Access Control (RBAC)

## Overview
The system has two roles: **Admin** and **User**

## Role Definitions

### 👤 User Role
- Can perform most operations (create, read, update)
- Cannot delete critical data
- Cannot undo operations
- Cannot access admin-only endpoints

### 👑 Admin Role
- Full access to all operations
- Can delete data
- Can undo operations
- Can manage users
- Can access all reports and logs

---

## Access Control Matrix

### 🔓 Public Access (No Authentication)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/users/register/` | POST | Register new user |
| `/api/users/login/` | POST | Login and get JWT token |

---

### 👤 User Access (JWT Required)

#### Stock Operations
| Endpoint | Method | Access |
|----------|--------|--------|
| Create Group | POST | ✅ User |
| List Groups | GET | ✅ User |
| Delete Group | POST | ❌ Admin Only |
| Create Stock | POST | ✅ User |
| Update Stock | POST | ✅ User |
| Delete Stock | POST | ❌ Admin Only |
| Get All Stocks | GET | ✅ User |
| List Inventory | GET | ✅ User |
| Add Stock Quantity | POST | ✅ User |
| Subtract Stock Quantity | POST | ✅ User |
| Add Defective Goods | POST | ✅ User |
| Subtract Defective Goods | POST | ✅ User |
| Stock Descriptions | POST | ✅ User |
| Save Opening Stock | POST | ✅ User |
| Save Closing Stock | POST | ✅ User |

#### Production Operations
| Endpoint | Method | Access |
|----------|--------|--------|
| Create Product | POST | ✅ User |
| Update Product | POST | ✅ User |
| Delete Product | POST | ❌ Admin Only |
| Get All Products | POST | ✅ User |
| Alter Components | POST | ✅ User |
| Push to Production | POST | ✅ User |
| Undo Production | POST | ❌ Admin Only |
| Delete Push Record | POST | ❌ Admin Only |
| Get Production Reports | POST | ✅ User |

#### Casting Operations
| Endpoint | Method | Access |
|----------|--------|--------|
| Create Casting Product | POST | ✅ User |
| Move to Production | POST | ✅ User |
| Delete Casting Product | POST | ✅ User |
| Get All Casting Products | GET | ✅ User |

#### Reports Operations
| Endpoint | Method | Access |
|----------|--------|--------|
| Daily Consumption Summary | POST | ✅ User |
| Weekly Consumption Summary | POST | ✅ User |
| Monthly Consumption Summary | POST | ✅ User |
| Daily/Weekly/Monthly Inward | POST | ✅ User |
| All Stock Transactions | POST | ✅ User |
| Today's Logs | POST | ✅ User |
| Item History | POST | ✅ User |
| Monthly Inward/Outward Grid | POST | ✅ User |
| Production Summaries | POST | ✅ User |

#### Freight Operations
| Endpoint | Method | Access |
|----------|--------|--------|
| Create Freight Note | POST | ✅ User |
| Get Freight Note | POST | ✅ User |
| List Freight Notes | POST | ✅ User |
| Update Freight Note | POST | ✅ User |
| Delete Freight Note | POST | ❌ Admin Only |

#### GRN Operations
| Endpoint | Method | Access |
|----------|--------|--------|
| Create GRN | POST | ✅ User |
| Get GRN | GET | ✅ User |
| Delete GRN | DELETE | ❌ Admin Only |
| Get by Transport | GET | ✅ User |
| Get by Supplier | GET | ✅ User |
| List All GRN | GET | ✅ User |

---

### 👑 Admin-Only Access

| Endpoint | Method | Description |
|----------|--------|-------------|
| Delete Stock | POST | Permanently delete stock items |
| Delete Group | POST | Delete stock groups |
| Delete Product | POST | Delete production products |
| Undo Production | POST | Reverse production operations |
| Delete Push Record | POST | Delete production push records |
| Undo Action | POST | Undo any logged action |
| Delete Transaction Data | POST | Delete all transaction history |
| Delete Freight Note | POST | Delete freight records |
| Delete GRN | DELETE | Delete GRN records |
| Admin View Users | POST | View all users |
| Admin Update User | POST | Update user roles/passwords |

---

## Implementation Details

### Decorators Used
```python
@jwt_required          # Requires valid JWT token (any authenticated user)
@admin_required        # Requires JWT token + admin role
```

### Decorator Order
```python
@csrf_exempt
@require_http_methods([...])
@jwt_required          # First: Authenticate user
@admin_required        # Second: Check admin role
def my_view(request):
    pass
```

### Error Responses

#### 401 Unauthorized
```json
{
  "error": "Authentication required"
}
```
or
```json
{
  "error": "Invalid or expired token"
}
```

#### 403 Forbidden
```json
{
  "error": "Admin access required"
}
```

---

## Usage Examples

### User Operations (Regular User)
```bash
# Login as user
curl -X POST http://api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "pass123"}'

# Response: {"token": "...", "role": "user"}

# Create stock (allowed)
curl -X POST http://api/stock/create-stock/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{...}'

# Delete stock (forbidden - returns 403)
curl -X POST http://api/stock/delete-stock/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### Admin Operations
```bash
# Login as admin
curl -X POST http://api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Response: {"token": "...", "role": "admin"}

# Delete stock (allowed)
curl -X POST http://api/stock/delete-stock/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "item1", "username": "admin"}'
```

---

## Security Best Practices

1. **Default Role**: New users get "user" role by default
2. **Admin Creation**: First admin must be created manually or via migration
3. **Token Security**: Tokens expire after 6 hours
4. **Role Validation**: Role is embedded in JWT and validated on each request
5. **Audit Trail**: All operations are logged with username

---

## Creating First Admin User

### Option 1: Via API (if no users exist)
```bash
curl -X POST http://api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123", "role": "admin"}'
```

### Option 2: Via Django Shell
```python
python manage.py shell

from backend.dynamodb_service import dynamodb_service
import hashlib

dynamodb_service.put_item('USERS', {
    'username': 'admin',
    'password': hashlib.sha256('admin123'.encode()).hexdigest(),
    'role': 'admin'
})
```

---

## Summary

- **2 Roles**: User and Admin
- **Public Endpoints**: 2 (register, login)
- **User Accessible**: ~50 endpoints (read, create, update operations)
- **Admin Only**: 10 endpoints (delete, undo operations)
- **Protection**: JWT + Role-based decorators
