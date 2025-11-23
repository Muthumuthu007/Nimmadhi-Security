# GRN Transport Filter Extension

## Overview
Extended GRN module with transport-based filtering using DynamoDB GSI for efficient querying.

## 📘 DynamoDB GSI Schema

### GSI Details:
- **GSI Name**: `transport-index`
- **Partition Key**: `transport` (String)
- **Sort Key**: `date` (String)
- **Projection**: ALL attributes
- **Billing**: Inherits from main table (Pay-per-request)

## 📘 New API Endpoint

### Get GRN by Transport Type
- **Method**: `GET`
- **URL**: `/api/grn/transport/{transportType}/`
- **Description**: Retrieves all GRN records filtered by transport type

#### Examples:
```
GET /api/grn/transport/Van/
GET /api/grn/transport/Mini Van/
GET /api/grn/transport/Truck/
GET /api/grn/transport/Bus/
GET /api/grn/transport/Auto/
GET /api/grn/transport/Lorry/
GET /api/grn/transport/Container/
```

#### Success Response (200):
```json
{
  "message": "Found 3 GRN records",
  "transport_type": "Van",
  "data": [
    {
      "grnId": "123e4567-e89b-12d3-a456-426614174000",
      "date": "2024-01-15",
      "supplierName": "ABC Suppliers Ltd",
      "rawMaterial": "Steel Rods",
      "billNumber": "BILL-2024-001",
      "billDate": "2024-01-14",
      "billedQuantity": 100.0,
      "receivedQuantity": 98.0,
      "transport": "Van",
      "tallyReference": "TALLY-REF-001",
      "costing": 5000.00,
      "taxPercentage": 18.0,
      "sgstAmount": 450.00,
      "cgstAmount": 450.00,
      "totalAmount": 5900.00,
      "created_at": "2024-01-15T10:30:00.000Z"
    },
    {
      "grnId": "456e7890-e89b-12d3-a456-426614174001",
      "date": "2024-01-16",
      "supplierName": "XYZ Materials",
      "rawMaterial": "Cement",
      "billNumber": "BILL-2024-002",
      "billDate": "2024-01-15",
      "billedQuantity": 50.0,
      "receivedQuantity": 50.0,
      "transport": "Van",
      "tallyReference": "TALLY-REF-002",
      "costing": 2500.00,
      "taxPercentage": 18.0,
      "sgstAmount": 225.00,
      "cgstAmount": 225.00,
      "totalAmount": 2950.00,
      "created_at": "2024-01-16T11:15:00.000Z"
    }
  ]
}
```

#### Empty Response (200):
```json
{
  "message": "No data found",
  "data": []
}
```

#### Error Response (500):
```json
{
  "error": "Internal error: [error message]"
}
```

## 📘 Sample Usage

### cURL Commands:
```bash
# Get all Van transport GRNs
curl -X GET http://localhost:8000/api/grn/transport/Van/

# Get all Mini Van transport GRNs
curl -X GET "http://localhost:8000/api/grn/transport/Mini%20Van/"

# Get all Truck transport GRNs
curl -X GET http://localhost:8000/api/grn/transport/Truck/

# Get all Bus transport GRNs
curl -X GET http://localhost:8000/api/grn/transport/Bus/

# Get all Auto transport GRNs
curl -X GET http://localhost:8000/api/grn/transport/Auto/

# Get all Lorry transport GRNs
curl -X GET http://localhost:8000/api/grn/transport/Lorry/

# Get all Container transport GRNs
curl -X GET http://localhost:8000/api/grn/transport/Container/
```

## 📘 Implementation Details

### Files Modified:
1. `/grn/views.py` - Added `get_grn_by_transport()` function
2. `/grn/urls.py` - Added transport filter URL pattern
3. `/backend/dynamodb_service.py` - Enhanced query support
4. `create_grn_gsi.py` - GSI creation script

### Key Features:
- ✅ GSI-based efficient querying
- ✅ Case-sensitive transport matching
- ✅ Support for any transport type
- ✅ Handles spaces in transport names (URL encoding)
- ✅ Returns all matching records
- ✅ Proper error handling
- ✅ Decimal to float conversion for JSON
- ✅ Comprehensive logging

### Performance Benefits:
- **GSI Query**: O(log n) complexity vs O(n) table scan
- **Efficient**: Only queries records with matching transport
- **Scalable**: Supports N number of GRN records per transport type
- **Fast**: Sub-second response times even with large datasets

### Transport Types Supported:
- Mini Van
- Bus  
- Van
- Truck
- Auto
- Lorry
- Container
- Any custom transport type

## 📘 Testing Examples

### Create Test Data:
```bash
# Create GRN with Van transport
curl -X POST http://localhost:8000/api/grn/create/ \
  -H "Content-Type: application/json" \
  -d '{"date":"2024-01-15","supplierName":"ABC Ltd","rawMaterial":"Steel","billNumber":"B001","billDate":"2024-01-14","billedQuantity":100,"receivedQuantity":98,"transport":"Van","tallyReference":"T001","costing":5000,"taxPercentage":18,"sgstAmount":450,"cgstAmount":450,"totalAmount":5900}'

# Create GRN with Mini Van transport  
curl -X POST http://localhost:8000/api/grn/create/ \
  -H "Content-Type: application/json" \
  -d '{"date":"2024-01-16","supplierName":"XYZ Ltd","rawMaterial":"Cement","billNumber":"B002","billDate":"2024-01-15","billedQuantity":50,"receivedQuantity":50,"transport":"Mini Van","tallyReference":"T002","costing":2500,"taxPercentage":18,"sgstAmount":225,"cgstAmount":225,"totalAmount":2950}'
```

### Query by Transport:
```bash
# Get Van records
curl -X GET http://localhost:8000/api/grn/transport/Van/

# Get Mini Van records (URL encoded)
curl -X GET "http://localhost:8000/api/grn/transport/Mini%20Van/"
```

## 📘 URL Encoding Notes

For transport types with spaces, use URL encoding:
- `Mini Van` → `Mini%20Van`
- `Heavy Truck` → `Heavy%20Truck`
- `Light Vehicle` → `Light%20Vehicle`

The API automatically handles URL decoding.