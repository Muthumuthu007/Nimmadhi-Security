# Freight Inward Note Module Documentation

## Overview

The Freight Inward Note module is designed to record and manage "To-Pay" transport scenarios where payments are made upon delivery. This module handles the recording of freight bills and the allocation of costs across multiple suppliers when a single truck carries materials from different suppliers.

## Core Features

### 1. Freight Inward Note Management
- **Header Information**: Date, Transport Vendor Name, Total Amount Paid, User who recorded it
- **Supplier Allocation**: One-to-Many relationship for cost distribution
- **Validation**: Ensures sum of allocations equals total freight amount
- **CRUD Operations**: Create, Read, Update, Delete freight notes

### 2. Data Validation
- **Amount Validation**: Total freight amount must equal sum of all allocations
- **Required Fields**: All essential fields are validated
- **Data Integrity**: Ensures consistent data across freight notes and allocations

## Database Structure

### DynamoDB Tables

#### 1. freight_inward
```
Primary Key: freight_id (String)
Attributes:
- freight_id: Unique identifier (UUID)
- transport_vendor: Name of transport company
- total_amount: Total freight amount (Decimal)
- date: Date of freight note (String, YYYY-MM-DD)
- created_by: User who created the record
- created_at: Timestamp of creation
- updated_at: Timestamp of last update
```

#### 2. freight_allocations
```
Primary Key: allocation_id (String)
Global Secondary Index: freight_id-index
Attributes:
- allocation_id: Unique identifier (UUID)
- freight_id: Reference to freight_inward record
- supplier_name: Name of supplier
- amount: Allocated amount for this supplier (Decimal)
- created_at: Timestamp of creation
```

## API Endpoints

### Lambda Handler Operations

All operations are accessible via the main lambda handler at `/api/lambda/` with POST requests containing an `operation` field.

#### 1. CreateFreightNote
**Purpose**: Create a new freight inward note with allocations

**Request**:
```json
{
  "operation": "CreateFreightNote",
  "transport_vendor": "ABC Transport Co.",
  "total_amount": 15000.00,
  "date": "2024-01-15",
  "created_by": "user123",
  "allocations": [
    {
      "supplier_name": "Supplier A",
      "amount": 8000.00
    },
    {
      "supplier_name": "Supplier B",
      "amount": 4000.00
    },
    {
      "supplier_name": "Supplier C",
      "amount": 3000.00
    }
  ]
}
```

**Response**:
```json
{
  "message": "Freight note created successfully",
  "freight_note": {
    "freight_id": "uuid-string",
    "transport_vendor": "ABC Transport Co.",
    "total_amount": 15000.00,
    "date": "2024-01-15",
    "created_by": "user123",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00",
    "allocations": [...]
  }
}
```

#### 2. GetFreightNote
**Purpose**: Retrieve a specific freight note with its allocations

**Request**:
```json
{
  "operation": "GetFreightNote",
  "freight_id": "uuid-string"
}
```

#### 3. ListFreightNotes
**Purpose**: List all freight notes with their allocations

**Request**:
```json
{
  "operation": "ListFreightNotes"
}
```

**Response**:
```json
{
  "freight_notes": [
    {
      "freight_id": "uuid-string",
      "transport_vendor": "ABC Transport Co.",
      "total_amount": 15000.00,
      "date": "2024-01-15",
      "allocations": [...]
    }
  ]
}
```

#### 4. UpdateFreightNote
**Purpose**: Update an existing freight note

**Request**:
```json
{
  "operation": "UpdateFreightNote",
  "freight_id": "uuid-string",
  "transport_vendor": "XYZ Transport Ltd.",
  "total_amount": 16000.00,
  "date": "2024-01-16",
  "allocations": [
    {
      "supplier_name": "Supplier A",
      "amount": 9000.00
    },
    {
      "supplier_name": "Supplier B",
      "amount": 7000.00
    }
  ]
}
```

#### 5. DeleteFreightNote
**Purpose**: Delete a freight note and all its allocations

**Request**:
```json
{
  "operation": "DeleteFreightNote",
  "freight_id": "uuid-string"
}
```

### Direct API Endpoints

Alternative endpoints accessible directly:

- `POST /api/freight/create/` - Create freight note
- `POST /api/freight/get/` - Get specific freight note
- `POST /api/freight/list/` - List all freight notes
- `POST /api/freight/update/` - Update freight note
- `POST /api/freight/delete/` - Delete freight note

## Setup Instructions

### 1. Database Setup
Run the table creation script:
```bash
python create_freight_tables.py
```

This creates:
- `freight_inward` table
- `freight_allocations` table with GSI on `freight_id`

### 2. Application Configuration
The freight app is already configured in:
- `settings.py` - Added to INSTALLED_APPS and DynamoDB tables
- `urls.py` - Added routing for freight operations
- Main URL configuration includes freight endpoints

### 3. Testing
Run the test script to verify functionality:
```bash
python test_freight_api.py
```

## Business Logic

### Validation Rules

1. **Amount Validation**: The sum of all allocation amounts must exactly equal the total freight amount
2. **Required Fields**: 
   - transport_vendor (cannot be empty)
   - total_amount (must be positive)
   - date (must be valid date format)
   - allocations (at least one allocation required)
3. **Allocation Validation**:
   - Each allocation must have supplier_name
   - Each allocation must have positive amount

### Error Handling

- **400 Bad Request**: Validation errors, missing required fields
- **404 Not Found**: Freight note not found
- **500 Internal Server Error**: Database or system errors

### Data Consistency

- **Atomic Operations**: Freight note and allocations are created/updated together
- **Cleanup on Error**: If freight creation fails, any partial data is cleaned up
- **Referential Integrity**: Allocations are automatically deleted when freight note is deleted

## Usage Examples

### Example 1: Single Truck, Multiple Suppliers
```json
{
  "operation": "CreateFreightNote",
  "transport_vendor": "Fast Logistics",
  "total_amount": 25000.00,
  "date": "2024-01-20",
  "created_by": "warehouse_manager",
  "allocations": [
    {
      "supplier_name": "Steel Corp",
      "amount": 15000.00
    },
    {
      "supplier_name": "Aluminum Ltd",
      "amount": 6000.00
    },
    {
      "supplier_name": "Copper Industries",
      "amount": 4000.00
    }
  ]
}
```

### Example 2: Update Allocation Distribution
```json
{
  "operation": "UpdateFreightNote",
  "freight_id": "existing-uuid",
  "total_amount": 25000.00,
  "allocations": [
    {
      "supplier_name": "Steel Corp",
      "amount": 12000.00
    },
    {
      "supplier_name": "Aluminum Ltd",
      "amount": 8000.00
    },
    {
      "supplier_name": "Copper Industries",
      "amount": 5000.00
    }
  ]
}
```

## Integration Points

### With Existing Modules
- **Users Module**: Uses user authentication for created_by field
- **Reports Module**: Can be extended to include freight cost analysis
- **Stock Module**: Can be linked to track which stock items were delivered

### Future Enhancements
1. **GRN Integration**: Link freight notes to Goods Receipt Notes
2. **Supplier Master**: Integration with supplier management
3. **Cost Center Allocation**: Distribute costs to different departments
4. **Approval Workflow**: Multi-level approval for high-value freight
5. **Document Attachment**: Store freight bill images/PDFs

## Security Considerations

- **Input Validation**: All inputs are validated before processing
- **SQL Injection Prevention**: Using DynamoDB with parameterized queries
- **Authentication**: Requires valid user session (when integrated with auth)
- **Authorization**: Can be extended to include role-based access control

## Performance Considerations

- **DynamoDB Optimization**: Uses efficient key structures and GSI
- **Batch Operations**: Allocations are processed in batch for efficiency
- **Caching**: Can be extended with Redis/ElastiCache for frequently accessed data
- **Pagination**: List operations can be extended with pagination for large datasets

## Monitoring and Logging

- **Application Logs**: All operations are logged with timestamps
- **Error Tracking**: Detailed error messages for troubleshooting
- **Audit Trail**: Created/updated timestamps for all records
- **Performance Metrics**: Can be extended with CloudWatch integration