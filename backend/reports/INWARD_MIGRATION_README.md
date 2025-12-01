# Daily Inward Lambda to Django Migration

## Overview

This document outlines the complete migration of the `get_daily_inward` function from AWS Lambda to the Django Reports application. The migration maintains 100% functional compatibility with the original Lambda implementation.

## Files Created/Modified

### New Files
- `reports/inward_service.py` - Core service containing exact Lambda port
- `reports/test_inward_fixtures.py` - Sample data for testing
- `reports/test_inward_command.py` - Test script for verification

### Modified Files
- `reports/views.py` - Updated inward endpoints to use new service
- `reports/urls.py` - Already configured for inward endpoints

## Architecture Changes

### Lambda vs Django Comparison

| Aspect | Lambda Implementation | Django Implementation |
|--------|----------------------|----------------------|
| **Entry Point** | `get_daily_inward(body)` | `InwardService.get_daily_inward(report_date)` |
| **Data Access** | Direct DynamoDB calls | `dynamodb_service` wrapper |
| **Error Handling** | Lambda response format | Django JsonResponse |
| **Date Handling** | IST timezone (+5:30) | Same IST logic preserved |
| **Business Logic** | Embedded in function | Extracted to service class |

### Key Components Migrated

1. **`_get_inward_data()` Helper Function**
   - Aggregates AddStockQuantity transactions
   - Calculates existing vs new quantities
   - Fetches stock names from stock table

2. **`get_group_chain()` Function**
   - Builds hierarchical group chains
   - Walks up parent_id relationships
   - Returns ordered chain [parent, ..., child]

3. **Group Nesting Logic**
   - Groups inward data by date → group → subgroup
   - Handles "Unknown" fallbacks for missing groups
   - Maintains exact Lambda structure

4. **IST Date Handling**
   - Defaults to current IST date (UTC + 5:30)
   - Preserves Lambda's date calculation logic

## API Endpoints

### Daily Inward Report
```http
POST /reports/inward/daily/
Content-Type: application/json

{
  "report_date": "2024-01-15"  // Optional, defaults to today IST
}
```

**Response Structure:**
```json
{
  "report_period": {
    "start_date": "2024-01-15",
    "end_date": "2024-01-15"
  },
  "inward": {
    "2024-01-15": {
      "Construction Materials": {
        "Building Supplies": [
          {
            "stock_name": "Steel Rods 12mm",
            "existing_quantity": 50.0,
            "inward_quantity": 100.0,
            "new_quantity": 150.0,
            "added_cost": 5000.0,
            "date": "2024-01-15"
          }
        ]
      }
    }
  }
}
```

### Weekly Inward Report
```http
POST /reports/inward/weekly/
Content-Type: application/json

{
  "start_date": "2024-01-15",  // Optional, defaults to 7 days ago
  "end_date": "2024-01-21"     // Optional, defaults to today IST
}
```

**Additional Response Fields:**
- `total_inward_quantity`: Sum of all inward quantities
- `total_inward_amount`: Sum of all inward costs

## Data Dependencies

### Required DynamoDB Tables

1. **stock_transactions**
   - Contains `AddStockQuantity` operations
   - Fields: `operation_type`, `date`, `details.item_id`, `details.quantity_added`, etc.

2. **stock** (configured as 'stock' in dynamodb_service)
   - Contains stock item details
   - Fields: `item_id`, `name`, `group_id`

3. **Groups** (configured as 'Groups' in dynamodb_service)
   - Contains group hierarchy
   - Fields: `group_id`, `name`, `parent_id`

### Sample Data Structure

**Transaction Record:**
```json
{
  "transaction_id": "txn_001",
  "date": "2024-01-15",
  "operation_type": "AddStockQuantity",
  "details": {
    "item_id": "steel_rod_001",
    "quantity_added": 100.0,
    "new_available": 150.0,
    "added_cost": 5000.0,
    "username": "admin"
  }
}
```

**Stock Item:**
```json
{
  "item_id": "steel_rod_001",
  "name": "Steel Rods 12mm",
  "group_id": "construction_materials",
  "cost_per_unit": 50.0
}
```

**Group Record:**
```json
{
  "group_id": "construction_materials",
  "name": "Construction Materials",
  "parent_id": "raw_materials"
}
```

## Testing & Verification

### Manual Testing
```bash
# Run test script
python manage.py shell < reports/test_inward_command.py

# Test daily inward via API
curl -X POST http://localhost:8000/reports/inward/daily/ \
  -H "Content-Type: application/json" \
  -d '{"report_date": "2024-01-15"}'

# Test weekly inward via API  
curl -X POST http://localhost:8000/reports/inward/weekly/ \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2024-01-15", "end_date": "2024-01-21"}'
```

### Expected Behavior Verification

1. **Date Handling**: Verify IST timezone calculation matches Lambda
2. **Group Nesting**: Confirm hierarchical structure matches Lambda output
3. **Data Aggregation**: Validate quantity and cost calculations
4. **Error Handling**: Test with missing data, invalid dates
5. **Performance**: Compare response times with Lambda (should be similar)

## Deployment Checklist

### Pre-Deployment
- [ ] Verify DynamoDB table configurations in `settings.py`
- [ ] Test with production-like data volume
- [ ] Validate AWS credentials and permissions
- [ ] Run test script to verify functionality

### Deployment Steps
1. Deploy updated `reports/inward_service.py`
2. Deploy updated `reports/views.py`
3. Restart Django application
4. Run smoke tests on inward endpoints
5. Monitor logs for any errors

### Post-Deployment
- [ ] Verify API endpoints respond correctly
- [ ] Compare output with Lambda function (if still running)
- [ ] Monitor performance and error rates
- [ ] Update API documentation if needed

## Migration Benefits

1. **Maintainability**: Code is now part of main application codebase
2. **Testing**: Easier to write unit tests and integration tests
3. **Debugging**: Better error tracking and logging
4. **Performance**: Reduced cold start times vs Lambda
5. **Cost**: Potentially lower costs depending on usage patterns

## Rollback Plan

If issues arise, rollback steps:

1. Revert `reports/views.py` to previous version
2. Remove `reports/inward_service.py`
3. Restart Django application
4. Re-enable Lambda function if needed
5. Update load balancer/API gateway routing

## Future Enhancements

1. **Caching**: Add Redis caching for frequently accessed data
2. **Pagination**: Add pagination for large date ranges
3. **Filtering**: Add additional filtering options
4. **Export**: Add CSV/Excel export functionality
5. **Real-time**: Consider WebSocket updates for real-time data

## Support & Troubleshooting

### Common Issues

1. **No Data Returned**: Check DynamoDB table names in settings
2. **Group Hierarchy Issues**: Verify Groups table structure
3. **Date Format Errors**: Ensure dates are in YYYY-MM-DD format
4. **Permission Errors**: Check AWS credentials and DynamoDB permissions

### Debug Commands
```python
# Test DynamoDB connection
from backend.dynamodb_service import dynamodb_service
transactions = dynamodb_service.scan_table('stock_transactions')
print(f"Found {len(transactions)} transactions")

# Test group chain
from reports.inward_service import InwardService
chain = InwardService.get_group_chain('your_group_id')
print(f"Group chain: {chain}")
```

### Contact
For issues or questions regarding this migration, contact the development team.