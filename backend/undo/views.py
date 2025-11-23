import json
import uuid
import logging
from decimal import Decimal
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from backend.dynamodb_service import dynamodb_service
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

@csrf_exempt
@require_http_methods(["POST"])
def undo_action(request):
    """Undo action - converted from Lambda undo_action function"""
    try:
        body = json.loads(request.body)
        
        username = body.get('username')
        if not username:
            return JsonResponse({"error": "'username' is required"}, status=400)
        
        # Get undo_id from body or find latest active undo for user
        undo_id = body.get('undo_id')
        if not undo_id:
            # Find latest active undo for user
            undo_records = dynamodb_service.scan_table('undo_actions')
            active_records = [
                record for record in undo_records 
                if record.get('username') == username and record.get('status') == 'ACTIVE'
            ]
            
            if not active_records:
                return JsonResponse({"error": "No active undo records found for the user."}, status=404)
            
            # Sort by timestamp and get latest
            active_records.sort(key=lambda r: r.get('timestamp', ''), reverse=True)
            undo_id = active_records[0]['undo_id']
        
        # Get undo record
        record = dynamodb_service.get_item('undo_actions', {'undo_id': undo_id})
        if not record:
            return JsonResponse({"error": "Undo record not found."}, status=404)
        
        if record.get('status') != 'ACTIVE':
            return JsonResponse({"error": "This undo record is already undone."}, status=400)
        
        operation = record.get('operation')
        details = record.get('undo_details', {})
        
        # Execute undo based on operation type
        if operation == "CreateStock":
            # Delete the created stock item
            item_id = details.get('item_id')
            if item_id:
                dynamodb_service.delete_item('STOCK', {'item_id': item_id})
                
        elif operation == "UpdateStock":
            # Restore old state
            old_state = details.get('old_state', {})
            item_id = details.get('item_id')
            if item_id and old_state:
                old_state['item_id'] = item_id
                old_state['updated_at'] = datetime.now().isoformat()
                dynamodb_service.put_item('STOCK', old_state)
                
        elif operation == "DeleteStock":
            # Restore deleted item
            deleted_item = details.get('deleted_item', {})
            if deleted_item:
                dynamodb_service.put_item('STOCK', deleted_item)
                
        elif operation == "AddStockQuantity":
            # Subtract the added quantity
            item_id = details.get('item_id')
            quantity_added = details.get('quantity_added', 0)
            if item_id and quantity_added:
                existing = dynamodb_service.get_item('STOCK', {'item_id': item_id})
                if existing:
                    new_qty = existing.get('quantity', 0) - quantity_added
                    existing['quantity'] = max(0, new_qty)
                    existing['updated_at'] = datetime.now().isoformat()
                    dynamodb_service.put_item('STOCK', existing)
                    
        elif operation == "SubtractStockQuantity":
            # Add back the subtracted quantity
            item_id = details.get('item_id')
            quantity_subtracted = details.get('quantity_subtracted', 0)
            if item_id and quantity_subtracted:
                existing = dynamodb_service.get_item('STOCK', {'item_id': item_id})
                if existing:
                    new_qty = existing.get('quantity', 0) + quantity_subtracted
                    existing['quantity'] = new_qty
                    existing['updated_at'] = datetime.now().isoformat()
                    dynamodb_service.put_item('STOCK', existing)
                    
        elif operation == "AddDefectiveGoods":
            # Subtract the added defective quantity
            item_id = details.get('item_id')
            defective_added = details.get('defective_added', 0)
            if item_id and defective_added:
                existing = dynamodb_service.get_item('STOCK', {'item_id': item_id})
                if existing:
                    new_defective = existing.get('defective', 0) - defective_added
                    existing['defective'] = max(0, new_defective)
                    existing['updated_at'] = datetime.now().isoformat()
                    dynamodb_service.put_item('STOCK', existing)
                    
        elif operation == "PushToProduction":
            # This would restore stock consumed in production
            push_id = details.get('push_id')
            if push_id:
                # Get push record and restore stock
                push_record = dynamodb_service.get_item('PUSH_TO_PRODUCTION', {'push_id': push_id})
                if push_record:
                    stock_deductions = push_record.get('stock_deductions', {})
                    for item_id, deduction in stock_deductions.items():
                        existing = dynamodb_service.get_item('STOCK', {'item_id': item_id})
                        if existing:
                            new_qty = existing.get('quantity', 0) + deduction
                            existing['quantity'] = new_qty
                            existing['updated_at'] = datetime.now().isoformat()
                            dynamodb_service.put_item('STOCK', existing)
                    
                    # Mark push as undone
                    push_record['status'] = 'UNDONE'
                    push_record['undone_at'] = datetime.now().isoformat()
                    dynamodb_service.put_item('PUSH_TO_PRODUCTION', push_record)
        
        # Mark undo record as done
        record['status'] = 'DONE'
        record['completed_at'] = datetime.now().isoformat()
        dynamodb_service.put_item('undo_actions', record)
        
        logger.info(f"Undo action completed: {operation} for {username}")
        return JsonResponse({
            "message": f"Action '{operation}' undone successfully.",
            "operation": operation,
            "undo_id": undo_id
        })
        
    except Exception as e:
        logger.error(f"Error in undo_action: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def delete_transaction_data(request):
    """Delete transaction data - converted from Lambda delete_transaction_data function"""
    try:
        body = json.loads(request.body)
        
        required = ['username', 'confirm']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        username = body['username']
        confirm = body['confirm']
        
        if confirm != 'DELETE_ALL_TRANSACTIONS':
            return JsonResponse({"error": "Invalid confirmation"}, status=400)
        
        # Delete all transaction data (admin only)
        tables_to_clear = ['stock_transactions', 'undo_actions', 'PUSH_TO_PRODUCTION']
        deleted_count = 0
        
        for table_name in tables_to_clear:
            try:
                items = dynamodb_service.scan_table(table_name)
                for item in items:
                    # Get the primary key for each table
                    if table_name == 'stock_transactions':
                        key = {'transaction_id': item['transaction_id']}
                    elif table_name == 'undo_actions':
                        key = {'undo_id': item['undo_id']}
                    elif table_name == 'PUSH_TO_PRODUCTION':
                        key = {'push_id': item['push_id']}
                    
                    dynamodb_service.delete_item(table_name, key)
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"Error clearing {table_name}: {e}")
        
        logger.info(f"Transaction data deleted by {username}: {deleted_count} records")
        return JsonResponse({
            "message": "Transaction data deleted successfully",
            "deleted_count": deleted_count
        })
        
    except Exception as e:
        logger.error(f"Error in delete_transaction_data: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)