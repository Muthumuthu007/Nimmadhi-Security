"""
Sample data fixtures for testing InwardService
Provides realistic test data matching Lambda function patterns
"""

# Sample stock transactions for inward operations
SAMPLE_INWARD_TRANSACTIONS = [
    {
        "transaction_id": "txn_20240115_001",
        "date": "2024-01-15",
        "timestamp": "2024-01-15 10:30:00 AM",
        "operation_type": "AddStockQuantity",
        "details": {
            "item_id": "steel_rod_001",
            "quantity_added": 100.0,
            "new_available": 150.0,
            "added_cost": 5000.0,
            "cost_per_unit": 50.0,
            "username": "admin"
        }
    },
    {
        "transaction_id": "txn_20240115_002",
        "date": "2024-01-15", 
        "timestamp": "2024-01-15 02:15:00 PM",
        "operation_type": "AddStockQuantity",
        "details": {
            "item_id": "cement_bag_001",
            "quantity_added": 50.0,
            "new_available": 75.0,
            "added_cost": 2500.0,
            "cost_per_unit": 50.0,
            "username": "warehouse_manager"
        }
    },
    {
        "transaction_id": "txn_20240116_001",
        "date": "2024-01-16",
        "timestamp": "2024-01-16 09:00:00 AM", 
        "operation_type": "AddStockQuantity",
        "details": {
            "item_id": "steel_rod_001",
            "quantity_added": 25.0,
            "new_available": 175.0,
            "added_cost": 1250.0,
            "cost_per_unit": 50.0,
            "username": "admin"
        }
    }
]

# Sample stock items with group hierarchy
SAMPLE_STOCK_ITEMS = [
    {
        "item_id": "steel_rod_001",
        "name": "Steel Rods 12mm",
        "group_id": "construction_materials",
        "cost_per_unit": 50.0,
        "available_quantity": 175.0,
        "unit": "pieces"
    },
    {
        "item_id": "cement_bag_001",
        "name": "Portland Cement 50kg",
        "group_id": "building_supplies",
        "cost_per_unit": 50.0,
        "available_quantity": 75.0,
        "unit": "bags"
    },
    {
        "item_id": "paint_bucket_001",
        "name": "Wall Paint White 20L",
        "group_id": "finishing_materials",
        "cost_per_unit": 150.0,
        "available_quantity": 30.0,
        "unit": "buckets"
    }
]

# Sample group hierarchy matching Lambda structure
SAMPLE_GROUPS = [
    {
        "group_id": "raw_materials",
        "name": "Raw Materials",
        "parent_id": None,
        "description": "Top-level raw materials category"
    },
    {
        "group_id": "construction_materials", 
        "name": "Construction Materials",
        "parent_id": "raw_materials",
        "description": "Basic construction materials"
    },
    {
        "group_id": "building_supplies",
        "name": "Building Supplies", 
        "parent_id": "construction_materials",
        "description": "Essential building supplies"
    },
    {
        "group_id": "finishing_materials",
        "name": "Finishing Materials",
        "parent_id": "raw_materials", 
        "description": "Materials for finishing work"
    }
]

# Expected nested output structure for daily inward
EXPECTED_DAILY_INWARD_OUTPUT = {
    "report_period": {
        "start_date": "2024-01-15",
        "end_date": "2024-01-15"
    },
    "inward": {
        "2024-01-15": {
            "Raw Materials": {
                "Construction Materials": [
                    {
                        "stock_name": "Steel Rods 12mm",
                        "existing_quantity": 50.0,
                        "inward_quantity": 100.0,
                        "new_quantity": 150.0,
                        "added_cost": 5000.0,
                        "date": "2024-01-15"
                    }
                ],
                "Building Supplies": [
                    {
                        "stock_name": "Portland Cement 50kg",
                        "existing_quantity": 25.0,
                        "inward_quantity": 50.0,
                        "new_quantity": 75.0,
                        "added_cost": 2500.0,
                        "date": "2024-01-15"
                    }
                ]
            }
        }
    }
}

# Expected weekly inward output structure
EXPECTED_WEEKLY_INWARD_OUTPUT = {
    "report_period": {
        "start_date": "2024-01-15",
        "end_date": "2024-01-16"
    },
    "inward": {
        "2024-01-15": {
            "Raw Materials": {
                "Construction Materials": [
                    {
                        "stock_name": "Steel Rods 12mm",
                        "existing_quantity": 50.0,
                        "inward_quantity": 100.0,
                        "new_quantity": 150.0,
                        "added_cost": 5000.0,
                        "date": "2024-01-15"
                    }
                ],
                "Building Supplies": [
                    {
                        "stock_name": "Portland Cement 50kg", 
                        "existing_quantity": 25.0,
                        "inward_quantity": 50.0,
                        "new_quantity": 75.0,
                        "added_cost": 2500.0,
                        "date": "2024-01-15"
                    }
                ]
            }
        },
        "2024-01-16": {
            "Raw Materials": {
                "Construction Materials": [
                    {
                        "stock_name": "Steel Rods 12mm",
                        "existing_quantity": 150.0,
                        "inward_quantity": 25.0,
                        "new_quantity": 175.0,
                        "added_cost": 1250.0,
                        "date": "2024-01-16"
                    }
                ]
            }
        }
    },
    "total_inward_quantity": 175.0,
    "total_inward_amount": 8750.0
}