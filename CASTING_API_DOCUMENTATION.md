# Product Casting APIs

This document describes the three new APIs for the Product Casting feature that allows users to estimate product costs before finalizing production.

## Overview

The casting feature provides a temporary product creation system where users can:
1. Create casting products to estimate costs
2. Move casting products to production when ready
3. Delete casting products if not needed

## API Endpoints

### 1. Create Casting Product

**Operation**: `CreateCastingProduct`

**Description**: Creates a temporary casting product with the same functionality as the existing Create Product API.

**Request Body**:
```json
{
  "operation": "CreateCastingProduct",
  "product_name": "Sample Product",
  "stock_needed": {
    "item_id_1": 10,
    "item_id_2": 5
  },
  "username": "user123",
  "wastage_percent": 5.0,
  "transport_cost": 100.0,
  "labour_cost": 200.0,
  "other_cost": 50.0
}
```

**Response**:
```json
{
  "message": "Casting product created successfully",
  "product_id": "uuid-string",
  "production_cost_total": 1500.0,
  "wastage_percent": 5.0,
  "wastage_amount": 75.0,
  "transport_cost": 100.0,
  "labour_cost": 200.0,
  "other_cost": 50.0,
  "total_cost": 1925.0
}
```

### 2. Move to Production

**Operation**: `MoveToProduction`

**Description**: Moves a casting product to the main production products list.

**Request Body**:
```json
{
  "operation": "MoveToProduction",
  "product_id": "casting-product-uuid",
  "username": "user123"
}
```

**Response**:
```json
{
  "message": "Casting product moved to production successfully",
  "product_id": "uuid-string",
  "production_cost_total": 1500.0,
  "wastage_percent": 5.0,
  "wastage_amount": 75.0,
  "transport_cost": 100.0,
  "labour_cost": 200.0,
  "other_cost": 50.0,
  "total_cost": 1925.0
}
```

### 3. Delete Casting Product

**Operation**: `DeleteCastingProduct`

**Description**: Deletes a casting product from the system.

**Request Body**:
```json
{
  "operation": "DeleteCastingProduct",
  "product_id": "casting-product-uuid",
  "username": "user123"
}
```

**Response**:
```json
{
  "message": "Casting product 'uuid-string' deleted successfully."
}
```

## Usage Flow

1. **Cost Estimation**: Use `CreateCastingProduct` to create temporary products and see estimated costs
2. **Decision Making**: Review the cost breakdown and decide whether to proceed
3. **Finalization**: Use `MoveToProduction` to convert casting product to production product
4. **Cleanup**: Use `DeleteCastingProduct` to remove unwanted casting products

## Error Handling

All APIs return appropriate HTTP status codes:
- `200`: Success
- `400`: Bad Request (missing required fields, invalid data)
- `404`: Not Found (product not found)
- `500`: Internal Server Error

## Database Schema

The casting products are stored in a separate `CastingProduct` model with identical structure to the main `Product` model, ensuring consistency in data format and API responses.