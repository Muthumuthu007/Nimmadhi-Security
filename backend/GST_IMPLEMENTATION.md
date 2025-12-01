# GST Implementation in Stock Management System

## Overview
Added GST (Goods and Services Tax) functionality to the Stock table and related APIs. The system now calculates GST amount and total cost including GST for all stock operations.

## Database Schema Changes

### STOCK Table (DynamoDB)
```json
{
  "item_id": "string",
  "name": "string", 
  "quantity": "number",
  "defective": "number",
  "total_quantity": "number",
  "cost_per_unit": "decimal",
  "gst": "decimal",           // NEW: GST percentage (0-100)
  "gst_amount": "decimal",    // NEW: Calculated GST amount
  "total_cost": "decimal",    // UPDATED: Now includes GST
  "stock_limit": "decimal",
  "unit": "string",
  "group_id": "string",
  "username": "string",
  "created_at": "string",
  "updated_at": "string"
}
```

## API Changes

### 1. Create Stock API
**Endpoint**: `POST /api/stock/create/`

**Updated Request Payload**:
```json
{
  "name": "Steel Rod 12mm",
  "quantity": 100,
  "defective": 5,
  "cost_per_unit": 50.0,
  "gst": 18.0,              // NEW: GST percentage (required)
  "stock_limit": 20,
  "username": "admin",
  "unit": "pieces",
  "group_id": "group123"
}
```

**Updated Response**:
```json
{
  "message": "Stock created successfully.",
  "item_id": "Steel Rod 12mm",
  "quantity": 95,
  "total_quantity": 100,
  "cost_per_unit": 50.0,
  "gst": 18.0,              // NEW: GST percentage
  "gst_amount": 855.0,      // NEW: Calculated GST amount
  "total_cost": 5605.0,     // UPDATED: Base cost + GST
  "stock_limit": 20.0,
  "defective": 5,
  "unit": "pieces",
  "group_id": "group123"
}
```

**GST Calculation Logic**:
```python
available_qty = quantity - defective  # 100 - 5 = 95
base_cost = available_qty * cost_per_unit  # 95 * 50 = 4750
gst_amount = (base_cost * gst) / 100  # (4750 * 18) / 100 = 855
total_cost = base_cost + gst_amount  # 4750 + 855 = 5605
```

### 2. Add Stock Quantity API
**Endpoint**: `POST /api/stock/add-quantity/`

**Request Payload** (unchanged):
```json
{
  "name": "Steel Rod 12mm",
  "quantity_to_add": 50,
  "username": "admin",
  "supplier_name": "ABC Steel Ltd"
}
```

**Updated Response**:
```json
{
  "message": "Added 50.0 units to stock 'Steel Rod 12mm'.",
  "item_id": "Steel Rod 12mm",
  "quantity_added": 50.0,
  "new_available": 145.0,
  "new_total": 150.0,
  "gst": 18.0,              // NEW: GST percentage from existing stock
  "gst_amount": 450.0,      // NEW: GST for added quantity
  "added_cost": 2950.0,     // NEW: Cost including GST for added qty
  "new_total_cost": 8555.0, // UPDATED: Total cost including all GST
  "updated_at": "2024-01-15T10:30:00",
  "supplier_name": "ABC Steel Ltd"
}
```

**GST Calculation for Added Stock**:
```python
base_added_cost = quantity_to_add * cost_per_unit  # 50 * 50 = 2500
gst_amount = (base_added_cost * gst) / 100  # (2500 * 18) / 100 = 450
added_cost = base_added_cost + gst_amount  # 2500 + 450 = 2950
new_total_cost = old_total_cost + added_cost  # 5605 + 2950 = 8555
```

## Sample Database Entry

```json
{
  "item_id": "Steel Rod 12mm",
  "name": "Steel Rod 12mm",
  "quantity": 145,
  "defective": 5,
  "total_quantity": 150,
  "cost_per_unit": 50.0,
  "gst": 18.0,
  "gst_amount": 1305.0,
  "total_cost": 8555.0,
  "stock_limit": 20.0,
  "unit": "pieces",
  "group_id": "group123",
  "username": "admin",
  "created_at": "2024-01-15T10:00:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

## Reports API Updates

All report APIs now return GST information:

### Daily/Weekly/Monthly Reports
**Updated Response Structure**:
```json
{
  "report_date": "2024-01-15",
  "stock_summary": {
    "Group Name": {
      "Subgroup Name": [
        {
          "item_id": "Steel Rod 12mm",
          "total_quantity_consumed": 25.0,
          "total_quantity_added": 50.0,
          "total_added_cost": 2950.0,    // Includes GST
          "gst_amount": 450.0,           // NEW: GST component
          "suppliers": ["ABC Steel Ltd"]
        }
      ]
    }
  },
  "total_consumption_quantity": 25.0,
  "total_consumption_amount": 1475.0,      // Includes GST
  "total_inward_quantity": 50.0,
  "total_inward_amount": 2950.0            // Includes GST
}
```

## Validation Rules

1. **GST Percentage**: Must be between 0 and 100
2. **Required Field**: GST is mandatory for creating new stock
3. **Existing Stock**: GST is retrieved from existing stock records for add/subtract operations
4. **Precision**: All GST calculations use Decimal for accuracy

## Testing

Run the test suite:
```bash
python test_gst_functionality.py
```

## Migration Notes

- Existing stock records without GST will default to 0% GST
- All new stock creation requires GST percentage
- Reports will show GST-inclusive amounts for better financial tracking
- Transaction logs include GST breakdown for audit purposes

## Benefits

1. **Accurate Costing**: Total costs now reflect actual purchase prices including taxes
2. **Tax Compliance**: Proper GST tracking for accounting and compliance
3. **Financial Reporting**: Reports show true cost of inventory including taxes
4. **Audit Trail**: All GST calculations are logged in transaction history