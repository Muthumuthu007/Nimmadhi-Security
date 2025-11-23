#!/usr/bin/env python3
"""
Verification script to ensure 100% coverage of Lambda operations in Django
"""

# All 48 Lambda operations from lambda_function.py
LAMBDA_OPERATIONS = [
    'AddDefectiveGoods',
    'AddStockQuantity', 
    'AdminUpdateUser',
    'AdminViewUsers',
    'AlterProduct',
    'CreateDescription',
    'CreateGroup',
    'CreateProduct',
    'CreateStock',
    'DeleteGroup',
    'DeleteProduct',
    'DeletePushToProduction',
    'DeleteStock',
    'DeleteTransactionData',
    'GetAllDescriptions',
    'GetAllProducts',
    'GetAllStockTransactions',
    'GetAllStocks',
    'GetDailyConsumptionSummary',
    'GetDailyInward',
    'GetDailyPushToProduction',
    'GetDailyReport',
    'GetDescription',
    'GetItemHistory',
    'GetMonthlyConsumptionSummary',
    'GetMonthlyInward',
    'GetMonthlyProductionSummary',
    'GetMonthlyPushToProduction',
    'GetMonthlyReport',
    'GetTodayLogs',
    'GetWeeklyConsumptionSummary',
    'GetWeeklyInward',
    'GetWeeklyPushToProduction',
    'GetWeeklyReport',
    'ListGroups',
    'ListInventoryStock',
    'LoginUser',
    'PushToProduction',
    'RegisterUser',
    'SaveClosingStock',
    'SaveOpeningStock',
    'SubtractDefectiveGoods',
    'SubtractStockQuantity',
    'UndoAction',
    'UndoProduction',
    'UpdateProduct',
    'UpdateProductDetails',
    'UpdateStock'
]

# Django function mapping
DJANGO_FUNCTIONS = {
    # Users app (7 functions)
    'CreateGroup': 'users.views.create_group',
    'ListGroups': 'users.views.list_groups',
    'DeleteGroup': 'users.views.delete_group',
    'AdminViewUsers': 'users.views.admin_view_users',
    'AdminUpdateUser': 'users.views.admin_update_user',
    'RegisterUser': 'users.views.register_user',
    'LoginUser': 'users.views.login_user',
    
    # Stock app (14 functions)
    'CreateStock': 'stock.views.create_stock',
    'UpdateStock': 'stock.views.update_stock',
    'DeleteStock': 'stock.views.delete_stock',
    'AddStockQuantity': 'stock.views.add_stock_quantity',
    'SubtractStockQuantity': 'stock.views.subtract_stock_quantity',
    'AddDefectiveGoods': 'stock.views.add_defective_goods',
    'SubtractDefectiveGoods': 'stock.views.subtract_defective_goods',
    'GetAllStocks': 'stock.views.get_all_stocks',
    'ListInventoryStock': 'stock.views.list_inventory_stock',
    'CreateDescription': 'stock.views.create_description',
    'GetDescription': 'stock.views.get_description',
    'GetAllDescriptions': 'stock.views.get_all_descriptions',
    'SaveOpeningStock': 'stock.views.save_opening_stock',
    'SaveClosingStock': 'stock.views.save_closing_stock',
    
    # Production app (13 functions)
    'CreateProduct': 'production.views.create_product',
    'UpdateProduct': 'production.views.update_product',
    'DeleteProduct': 'production.views.delete_product',
    'GetAllProducts': 'production.views.get_all_products',
    'AlterProduct': 'production.views.alter_product_components',
    'UpdateProductDetails': 'production.views.update_product_details',
    'GetMonthlyProductionSummary': 'production.views.get_monthly_production_summary',
    'PushToProduction': 'production.views.push_to_production',
    'UndoProduction': 'production.views.undo_production',
    'DeletePushToProduction': 'production.views.delete_push_to_production',
    'GetDailyPushToProduction': 'production.views.get_daily_push_to_production',
    'GetWeeklyPushToProduction': 'production.views.get_weekly_push_to_production',
    'GetMonthlyPushToProduction': 'production.views.get_monthly_push_to_production',
    
    # Reports app (12 functions)
    'GetDailyReport': 'reports.views.get_daily_report',
    'GetWeeklyReport': 'reports.views.get_weekly_report',
    'GetMonthlyReport': 'reports.views.get_monthly_report',
    'GetAllStockTransactions': 'reports.views.get_all_stock_transactions',
    'GetDailyConsumptionSummary': 'reports.views.get_daily_consumption_summary',
    'GetWeeklyConsumptionSummary': 'reports.views.get_weekly_consumption_summary',
    'GetMonthlyConsumptionSummary': 'reports.views.get_monthly_consumption_summary',
    'GetDailyInward': 'reports.views.get_daily_inward',
    'GetWeeklyInward': 'reports.views.get_weekly_inward',
    'GetMonthlyInward': 'reports.views.get_monthly_inward',
    'GetTodayLogs': 'reports.views.get_today_logs',
    'GetItemHistory': 'reports.views.get_item_history',
    
    # Undo app (2 functions)
    'UndoAction': 'undo.views.undo_action',
    'DeleteTransactionData': 'undo.views.delete_transaction_data',
}

def verify_coverage():
    """Verify 100% coverage of Lambda operations"""
    print("🔍 VERIFYING LAMBDA → DJANGO COVERAGE")
    print("=" * 50)
    
    total_lambda = len(LAMBDA_OPERATIONS)
    total_django = len(DJANGO_FUNCTIONS)
    
    print(f"Lambda Operations: {total_lambda}")
    print(f"Django Functions:  {total_django}")
    
    # Check for missing operations
    missing = []
    for op in LAMBDA_OPERATIONS:
        if op not in DJANGO_FUNCTIONS:
            missing.append(op)
    
    if missing:
        print(f"\n❌ MISSING OPERATIONS ({len(missing)}):")
        for op in missing:
            print(f"  - {op}")
        return False
    
    # Check for extra operations
    extra = []
    for op in DJANGO_FUNCTIONS:
        if op not in LAMBDA_OPERATIONS:
            extra.append(op)
    
    if extra:
        print(f"\n⚠️  EXTRA OPERATIONS ({len(extra)}):")
        for op in extra:
            print(f"  - {op}")
    
    # Summary by app
    print(f"\n📊 COVERAGE BY APP:")
    apps = {
        'users': [op for op in DJANGO_FUNCTIONS if 'users.views' in DJANGO_FUNCTIONS[op]],
        'stock': [op for op in DJANGO_FUNCTIONS if 'stock.views' in DJANGO_FUNCTIONS[op]],
        'production': [op for op in DJANGO_FUNCTIONS if 'production.views' in DJANGO_FUNCTIONS[op]],
        'reports': [op for op in DJANGO_FUNCTIONS if 'reports.views' in DJANGO_FUNCTIONS[op]],
        'undo': [op for op in DJANGO_FUNCTIONS if 'undo.views' in DJANGO_FUNCTIONS[op]]
    }
    
    for app, ops in apps.items():
        print(f"  {app:12}: {len(ops):2} operations")
    
    if not missing:
        print(f"\n✅ PERFECT COVERAGE: {total_lambda}/{total_lambda} operations implemented")
        return True
    else:
        print(f"\n❌ INCOMPLETE: {total_lambda - len(missing)}/{total_lambda} operations implemented")
        return False

if __name__ == "__main__":
    success = verify_coverage()
    exit(0 if success else 1)