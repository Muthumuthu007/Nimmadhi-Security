"""
URL configuration for backend project.
"""
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def lambda_handler_view(request):
    """Main router that mimics the lambda_handler function"""
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    try:
        body = json.loads(request.body)
        operation = body.get('operation')
        
        if not operation:
            return JsonResponse({"error": "Missing 'operation' field"}, status=400)
        
        # Route to appropriate app based on operation
        if operation in ['AdminViewUsers', 'AdminUpdateUser', 'RegisterUser', 'LoginUser']:
            from users import views as users_views
            return getattr(users_views, operation.lower().replace('admin', 'admin_'))(request, body)
            
        elif operation in ['CreateGroup', 'ListGroups', 'DeleteGroup']:
            from stock import views as stock_views
            if operation == 'CreateGroup':
                return stock_views.creategroup(request, body)
            elif operation == 'ListGroups':
                return stock_views.listgroups(request, body)
            elif operation == 'DeleteGroup':
                return stock_views.deletegroup(request, body)
            
        elif operation in ['CreateStock', 'UpdateStock', 'DeleteStock', 'AddStockQuantity', 'SubtractStockQuantity', 'AddDefectiveGoods', 'SubtractDefectiveGoods', 'GetAllStocks', 'ListInventoryStock', 'CreateDescription', 'GetDescription', 'GetAllDescriptions', 'SaveOpeningStock', 'SaveClosingStock', 'UndoAction']:
            from stock import views as stock_views
            # Map operations to function names
            operation_map = {
                'CreateStock': 'create_stock',
                'UpdateStock': 'update_stock', 
                'DeleteStock': 'delete_stock',
                'AddStockQuantity': 'add_stock_quantity',
                'SubtractStockQuantity': 'subtract_stock_quantity',
                'AddDefectiveGoods': 'add_defective_goods',
                'SubtractDefectiveGoods': 'subtract_defective_goods',
                'GetAllStocks': 'get_all_stocks',
                'ListInventoryStock': 'list_inventory_stock',
                'CreateDescription': 'create_description',
                'GetDescription': 'get_description',
                'GetAllDescriptions': 'get_all_descriptions',
                'SaveOpeningStock': 'save_opening_stock',
                'SaveClosingStock': 'save_closing_stock',
                'UndoAction': 'undo_action'
            }
            func_name = operation_map.get(operation)
            if func_name:
                return getattr(stock_views, func_name)(request)
            
        elif operation in ['CreateProduct', 'UpdateProduct', 'DeleteProduct', 'GetAllProducts', 'UpdateProductDetails', 'AlterProductComponents', 'PushToProduction', 'UndoProduction', 'DeletePushToProduction', 'GetDailyPushToProduction', 'GetWeeklyPushToProduction', 'GetMonthlyPushToProduction']:
            from production import views as production_views
            operation_map = {
                'CreateProduct': 'create_product',
                'UpdateProduct': 'update_product',
                'DeleteProduct': 'delete_product',
                'GetAllProducts': 'get_all_products',
                'UpdateProductDetails': 'update_product_details',
                'AlterProductComponents': 'alter_product_components',
                'PushToProduction': 'push_to_production',
                'UndoProduction': 'undo_production',
                'DeletePushToProduction': 'delete_push_to_production',
                'GetDailyPushToProduction': 'get_daily_push_to_production',
                'GetWeeklyPushToProduction': 'get_weekly_push_to_production',
                'GetMonthlyPushToProduction': 'get_monthly_push_to_production'
            }
            func_name = operation_map.get(operation)
            if func_name:
                request._body = json.dumps(body).encode('utf-8')
                return getattr(production_views, func_name)(request)
            
        elif operation in ['GetDailyReport', 'GetWeeklyReport', 'GetMonthlyReport', 'GetAllStockTransactions', 'GetDailyConsumptionSummary', 'GetWeeklyConsumptionSummary', 'GetMonthlyConsumptionSummary', 'GetDailyInward', 'GetWeeklyInward', 'GetMonthlyInward', 'GetTodayLogs', 'GetItemHistory', 'GetMonthlyProductionSummary']:
            from reports import views as reports_views
            return getattr(reports_views, operation.lower().replace('get', 'get_'))(request, body)
            
        elif operation in ['CreateCastingProduct', 'MoveToProduction', 'DeleteCastingProduct']:
            from casting import views as casting_views
            operation_map = {
                'CreateCastingProduct': 'create_casting_product',
                'MoveToProduction': 'move_to_production',
                'DeleteCastingProduct': 'delete_casting_product'
            }
            func_name = operation_map.get(operation)
            if func_name:
                return getattr(casting_views, func_name)(request, body)
                
        elif operation in ['DeleteTransactionData']:
            from stock import views as stock_views
            return stock_views.delete_transaction_data(request)
            
        else:
            return JsonResponse({"error": "Invalid operation"}, status=400)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

urlpatterns = [
    path('api/lambda/', lambda_handler_view, name='lambda_handler'),
    path('api/users/', include('users.urls')),
    path('api/stock/', include('stock.urls')),
    path('api/production/', include('production.urls')),
    path('api/casting/', include('casting.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/grn/', include('grn.urls')),
]