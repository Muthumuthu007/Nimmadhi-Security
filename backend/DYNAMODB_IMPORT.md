# DynamoDB Import Guide

This guide explains how to import your DynamoDB JSON exports into Django models.

## Files Created

1. **`management/commands/import_dynamodb.py`** - Basic import command
2. **`management/commands/import_dynamodb_auto.py`** - Enhanced auto-detection command
3. **`import_data.py`** - Simple utility script to run imports

## Directory Structure Expected

```
AWSDynamoDB/
├── <table1-export-id>/
│   ├── manifest-files.json (optional)
│   ├── manifest-summary.json (optional)
│   └── data/
│       ├── file1.json
│       ├── file2.json
│       └── ...
├── <table2-export-id>/
│   └── data/
│       ├── file1.json
│       └── ...
└── ...
```

## Usage Options

### Option 1: Using the Utility Script (Recommended)
```bash
cd /Users/muthuk/Downloads/backend
python import_data.py
```

### Option 2: Using Django Management Commands Directly

#### Basic Import Command
```bash
python manage.py import_dynamodb --data-dir AWSDynamoDB
```

#### Auto-Detection Command (Recommended)
```bash
python manage.py import_dynamodb_auto --data-dir AWSDynamoDB
```

#### Dry Run (Test without importing)
```bash
python manage.py import_dynamodb_auto --data-dir AWSDynamoDB --dry-run
```

#### Clear Existing Data Before Import
```bash
python manage.py import_dynamodb_auto --data-dir AWSDynamoDB --clear-tables
```

## Table to Model Mapping

The commands automatically map DynamoDB tables to Django models:

| DynamoDB Table | Django Model |
|----------------|--------------|
| `users` | `users.User` |
| `Groups` | `users.Group` |
| `stock` | `stock.Stock` |
| `stock_remarks` | `stock.StockRemarks` |
| `production` | `production.Product` |
| `push_to_production` | `production.PushToProduction` |
| `stock_transactions` | `undo.StockTransaction` |
| `undo_actions` | `undo.UndoAction` |

## DynamoDB JSON Format Conversion

The import automatically converts DynamoDB JSON format to Python types:

- `{"S": "value"}` → `"value"` (String)
- `{"N": "123"}` → `123` (Number)
- `{"BOOL": true}` → `True` (Boolean)
- `{"NULL": true}` → `None` (Null)
- `{"L": [...]}` → `[...]` (List)
- `{"M": {...}}` → `{...}` (Map/Dictionary)
- `{"SS": [...]}` → `[...]` (String Set)
- `{"NS": [...]}` → `[...]` (Number Set)

## Features

### Auto-Detection
- Automatically detects table names from manifest files
- Handles multiple JSON files per table
- Processes all tables in the export directory

### Error Handling
- Continues processing if individual records fail
- Reports success/failure counts per table
- Shows preview of problematic records

### Safety Features
- Dry-run mode to test before importing
- Optional clearing of existing data
- Transaction-based imports for data integrity

## Troubleshooting

### Common Issues

1. **Model not found error**
   - Ensure Django models exist and are properly registered
   - Check the table-to-model mapping in the command

2. **Field validation errors**
   - The command automatically truncates strings that exceed max_length
   - Converts Decimal to float for FloatField
   - Handles JSON field conversion

3. **Table name detection fails**
   - Ensure manifest files exist in export directories
   - Check that directory names follow expected patterns
   - Manually verify table names in the mapping

### Manual Table Name Detection

If auto-detection fails, you can modify the `table_model_mapping` dictionary in the command files to add custom mappings.

## Example Output

```
Found 8 table export directories
Detected table: users in directory 01234567-89ab-cdef-0123-456789abcdef
Detected table: stock in directory 98765432-10fe-dcba-9876-543210fedcba

Importing table: users
Found 2 JSON files
  Processing 150 records from file1.json
  Processing 75 records from file2.json
Successfully imported 225 records for table users

Importing table: stock
Found 1 JSON files
  Processing 500 records from file1.json
Successfully imported 500 records for table stock
```

## Next Steps

After importing:
1. Verify data integrity in Django admin
2. Run any necessary data migrations
3. Update sequences/auto-increment fields if needed
4. Test application functionality with imported data