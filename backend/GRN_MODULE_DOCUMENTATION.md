# GRN (Goods Received Note) Module Documentation

## Overview
Complete GRN module implementation with DynamoDB backend following your project's architecture patterns.

## 📘 DynamoDB Table Schema

### Table Name: `grn_table`
- **Primary Key**: `grnId` (String, UUID)
- **Billing Mode**: Pay-per-request
- **All other fields**: Normal attributes (no secondary indexes needed)

### Table Creation
Run the table creation script:
```bash
python create_grn_table.py
```

## 📘 GRN Data Model / DTO

### GRN Fields (Exact as specified)
```json
{
  "grnId": "string (UUID, Primary Key)",
  "serialNumber": "string",
  "date": "string",
  "supplierName": "string", 
  "rawMaterial": "string",
  "billNumber": "string",
  "billDate": "string",
  "billedQuantity": "number",
  "receivedQuantity": "number",
  "transport": "string",
  "tallyReference": "string",
  "costing": "number",
  "taxPercentage": "number",
  "sgstAmount": "number",
  "cgstAmount": "number",
  "totalAmount": "number",
  "created_at": "string (ISO timestamp, auto-generated)"
}
```

## 📘 API Endpoints

### 1. Create GRN
- **Method**: `POST`
- **URL**: `/api/grn/create/`
- **Description**: Creates a new GRN record

#### Request Body:
```json
{
  "serialNumber": "GRN-001",
  "date": "2024-01-15",
  "supplierName": "ABC Suppliers Ltd",
  "rawMaterial": "Steel Rods",
  "billNumber": "BILL-2024-001",
  "billDate": "2024-01-14",
  "billedQuantity": 100.0,
  "receivedQuantity": 98.0,
  "transport": "Truck Transport",
  "tallyReference": "TALLY-REF-001",
  "costing": 5000.00,
  "taxPercentage": 18.0,
  "sgstAmount": 450.00,
  "cgstAmount": 450.00,
  "totalAmount": 5900.00
}
```

#### Success Response (201):
```json
{
  "message": "GRN created successfully",
  "grnId": "123e4567-e89b-12d3-a456-426614174000",
  "serialNumber": "GRN-001",
  "date": "2024-01-15",
  "supplierName": "ABC Suppliers Ltd",
  "rawMaterial": "Steel Rods",
  "billNumber": "BILL-2024-001",
  "billDate": "2024-01-14",
  "billedQuantity": 100.0,
  "receivedQuantity": 98.0,
  "transport": "Truck Transport",
  "tallyReference": "TALLY-REF-001",
  "costing": 5000.00,
  "taxPercentage": 18.0,
  "sgstAmount": 450.00,
  "cgstAmount": 450.00,
  "totalAmount": 5900.00
}
```

#### Error Response (400):
```json
{
  "error": "'serialNumber' is required"
}
```

### 2. Get GRN
- **Method**: `GET`
- **URL**: `/api/grn/{grnId}/`
- **Description**: Retrieves a GRN record by ID

#### Success Response (200):
```json
{
  "grnId": "123e4567-e89b-12d3-a456-426614174000",
  "serialNumber": "GRN-001",
  "date": "2024-01-15",
  "supplierName": "ABC Suppliers Ltd",
  "rawMaterial": "Steel Rods",
  "billNumber": "BILL-2024-001",
  "billDate": "2024-01-14",
  "billedQuantity": 100.0,
  "receivedQuantity": 98.0,
  "transport": "Truck Transport",
  "tallyReference": "TALLY-REF-001",
  "costing": 5000.00,
  "taxPercentage": 18.0,
  "sgstAmount": 450.00,
  "cgstAmount": 450.00,
  "totalAmount": 5900.00,
  "created_at": "2024-01-15T10:30:00.000Z"
}
```

#### Error Response (404):
```json
{
  "error": "GRN not found"
}
```

### 3. Delete GRN
- **Method**: `DELETE`
- **URL**: `/api/grn/{grnId}/delete/`
- **Description**: Deletes a GRN record by ID

#### Success Response (200):
```json
{
  "message": "GRN deleted successfully",
  "grnId": "123e4567-e89b-12d3-a456-426614174000"
}
```

#### Error Response (404):
```json
{
  "error": "GRN not found"
}
```

## 📘 Sample API Usage

### Create GRN Example
```bash
curl -X POST http://localhost:8000/api/grn/create/ \
  -H "Content-Type: application/json" \
  -d '{
    "serialNumber": "GRN-001",
    "date": "2024-01-15",
    "supplierName": "ABC Suppliers Ltd",
    "rawMaterial": "Steel Rods",
    "billNumber": "BILL-2024-001",
    "billDate": "2024-01-14",
    "billedQuantity": 100.0,
    "receivedQuantity": 98.0,
    "transport": "Truck Transport",
    "tallyReference": "TALLY-REF-001",
    "costing": 5000.00,
    "taxPercentage": 18.0,
    "sgstAmount": 450.00,
    "cgstAmount": 450.00,
    "totalAmount": 5900.00
  }'
```

### Get GRN Example
```bash
curl -X GET http://localhost:8000/api/grn/123e4567-e89b-12d3-a456-426614174000/
```

### Delete GRN Example
```bash
curl -X DELETE http://localhost:8000/api/grn/123e4567-e89b-12d3-a456-426614174000/delete/
```

## 📘 Implementation Details

### Files Created:
1. `/grn/__init__.py` - App initialization
2. `/grn/apps.py` - App configuration
3. `/grn/models.py` - No Django models (DynamoDB only)
4. `/grn/views.py` - API view functions
5. `/grn/urls.py` - URL routing
6. `create_grn_table.py` - DynamoDB table creation script
7. Updated `backend/settings.py` - Added GRN app and table config
8. Updated `backend/urls.py` - Added GRN URL routing

### Key Features:
- ✅ UUID-based primary keys
- ✅ Decimal precision for financial fields
- ✅ Comprehensive error handling
- ✅ Logging for all operations
- ✅ JSON serialization with Decimal support
- ✅ Follows existing project patterns
- ✅ DynamoDB integration using existing service
- ✅ CSRF exempt decorators for API usage
- ✅ HTTP method restrictions

### Error Handling:
- Field validation for all required fields
- JSON parsing error handling
- DynamoDB operation error handling
- 404 handling for non-existent records
- 500 handling for internal errors

### Security:
- CSRF exempt (following project pattern)
- Input validation
- SQL injection prevention (NoSQL)
- Error message sanitization

## 📘 Testing the Module

### 1. Start Django Server
```bash
cd "/Users/muthuk/Downloads/backend 8/backend 4/backend"
python manage.py runserver
```

### 2. Create DynamoDB Table
```bash
python create_grn_table.py
```

### 3. Test APIs
Use the curl examples above or any API testing tool like Postman.

## 📘 Integration Notes

The GRN module is fully integrated into your existing Django project:
- Added to `INSTALLED_APPS`
- Added to `DYNAMODB_TABLES` configuration
- Added to main URL routing
- Uses existing `dynamodb_service`
- Follows existing logging patterns
- Uses existing error handling patterns