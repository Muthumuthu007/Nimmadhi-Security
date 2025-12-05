import json
import uuid
import logging
from decimal import Decimal
from datetime import datetime, timedelta
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from backend.dynamodb_service import dynamodb_service
from botocore.exceptions import ClientError
from users.decorators import jwt_required, admin_required
from users.jwt_utils import decode_jwt_token
from users.token_manager import TokenManager

logger = logging.getLogger(__name__)



class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

# Helper functions for stock operations
def log_transaction(action, data, username):
    """Log transaction for audit trail"""
    try:
        transaction_id = str(uuid.uuid4())
        transaction_data = {
            'transaction_id': transaction_id,
            'operation_type': action,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat(),
            'username': username,
            'details': data
        }
        dynamodb_service.put_item('stock_transactions', transaction_data)
        logger.info(f"Transaction logged: {action} by {username}")
    except Exception as e:
        logger.error(f"Error logging transaction: {e}")

def log_undo_action(action, data, username):
    """Log undo action for rollback capability"""
    try:
        undo_id = str(uuid.uuid4())
        undo_data = {
            'undo_id': undo_id,
            'operation': action,
            'undo_details': data,
            'username': username,
            'status': 'ACTIVE',
            'timestamp': datetime.now().isoformat()
        }
        dynamodb_service.put_item('undo_actions', undo_data)
        logger.info(f"Undo action logged: {action} by {username}")
    except Exception as e:
        logger.error(f"Error logging undo action: {e}")

def recalc_all_production():
    """Recalculate production maxima after stock changes"""
    try:
        # This would recalculate max_produce for all products
        # For now, just log the action
        logger.info("Recalculating production maxima")
    except Exception as e:
        logger.error(f"Error recalculating production: {e}")

@csrf_exempt
@require_http_methods(["GET", "POST"])
@jwt_required
def get_all_stock_transactions(request):
    """Get all stock transactions for reporting"""
    try:
        transactions = dynamodb_service.scan_table('stock_transactions')
        return JsonResponse(transactions, safe=False)
    except Exception as e:
        logger.error(f"Error getting stock transactions: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

def get_existing_stock_record(operation, date_str):
    """Check if stock record exists for given operation and date with enhanced reliability"""
    try:
        # Get all transactions
        transactions = dynamodb_service.scan_table('stock_transactions')
        
        # Search for matching record
        for transaction in transactions:
            trans_op = transaction.get('operation_type')
            trans_date = transaction.get('date')
            
            if trans_op == operation and trans_date == date_str:
                logger.info(f"Found {operation} record for {date_str}: {transaction.get('transaction_id')}")
                return transaction
        
        logger.info(f"No {operation} record found for {date_str}")
        return None
        
    except Exception as e:
        logger.error(f"Error in get_existing_stock_record: {e}")
        return None

def ensure_stock_remarks_table():
    """Ensure stock_remarks table exists"""
    try:
        # In Django implementation, table creation is handled by dynamodb_service
        logger.info("Stock remarks table ensured")
    except Exception as e:
        logger.error(f"Error ensuring stock remarks table: {e}")

def get_undo_record(undo_id):
    """Get undo record by ID"""
    try:
        return dynamodb_service.get_item('undo_actions', {'undo_id': undo_id})
    except Exception as e:
        logger.error(f"Error getting undo record: {e}")
        return None

def mark_undo_as_done(undo_id):
    """Mark undo action as completed"""
    try:
        existing = dynamodb_service.get_item('undo_actions', {'undo_id': undo_id})
        if existing:
            existing['status'] = 'DONE'
            existing['completed_at'] = datetime.now().isoformat()
            dynamodb_service.put_item('undo_actions', existing)
        return True
    except Exception as e:
        logger.error(f"Error marking undo as done: {e}")
        return False

# Stub functions for all required endpoints
@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def create_group(request):
    try:
        body = json.loads(request.body)
        
        if 'name' not in body:
            return JsonResponse({"error": "'name' is required"}, status=400)

        name = body['name']
        parent_id = body.get('parent_id')  # may be None
        group_id = str(uuid.uuid4())

        # Create group in DynamoDB
        group_item = {
            'group_id': group_id,
            'name': name
        }
        if parent_id:
            group_item['parent_id'] = parent_id
        
        dynamodb_service.put_item('GROUPS', group_item)
        
        logger.info(f"Group created: {group_id} ('{name}', parent={parent_id})")

        return JsonResponse({
            "message": "Group created successfully",
            "group_id": group_id,
            "name": name,
            "parent_id": parent_id
        })
        
    except Exception as e:
        logger.error(f"Error in create_group: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
@admin_required
def delete_group(request):
    try:
        body = json.loads(request.body)
        
        if 'group_id' not in body:
            return JsonResponse({"error": "'group_id' is required"}, status=400)

        group_id = body['group_id']
        
        # Check if group exists
        existing = dynamodb_service.get_item('GROUPS', {'group_id': group_id})
        if not existing:
            return JsonResponse({"error": "Group not found"}, status=404)
        
        # Delete the group
        dynamodb_service.delete_item('GROUPS', {'group_id': group_id})
        
        logger.info(f"Group deleted: {group_id}")
        return JsonResponse({
            "message": "Group deleted successfully",
            "group_id": group_id
        })
        
    except Exception as e:
        logger.error(f"Error in delete_group: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@jwt_required
def list_groups(request):
    try:
        parent_id = request.GET.get('parent_id')
        logger.info(f"Fetching groups with parent_id: {parent_id}")
        
        try:
            if parent_id:
                # Query groups with specific parent_id
                groups = dynamodb_service.scan_table(
                    'GROUPS', 
                    FilterExpression='parent_id = :pid', 
                    ExpressionAttributeValues={':pid': parent_id}
                )
            else:
                # Get root groups (no parent_id)
                groups = dynamodb_service.scan_table(
                    'GROUPS', 
                    FilterExpression='attribute_not_exists(parent_id)'
                )
            
            logger.info(f"Found {len(groups)} groups")
            return JsonResponse({"groups": groups}, safe=False)
            
        except ClientError as e:
            logger.error(f"DynamoDB error fetching groups: {e}")
            return JsonResponse({"error": "Failed to fetch groups from database"}, status=500)
        
    except Exception as e:
        logger.error(f"Error in list_groups: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def debug_token(request):
    """Debug endpoint to test JWT token validation"""
    try:
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if not auth_header:
            return JsonResponse({
                "error": "No Authorization header found",
                "headers_received": {k: v for k, v in request.META.items() if k.startswith('HTTP_')}
            }, status=401)
        
        if not auth_header.startswith('Bearer '):
            return JsonResponse({
                "error": "Authorization header must start with 'Bearer '",
                "received": auth_header[:50]
            }, status=401)
        
        token = auth_header.split(' ')[1]
        
        # Check blacklist
        if TokenManager.is_token_blacklisted(token):
            return JsonResponse({"error": "Token is blacklisted"}, status=401)
        
        # Decode token
        payload = decode_jwt_token(token)
        if not payload:
            return JsonResponse({
                "error": "Token decode failed - invalid or expired",
                "token_preview": token[:20] + "..."
            }, status=401)
        
        return JsonResponse({
            "message": "Token is valid",
            "payload": payload
        })
        
    except Exception as e:
        return JsonResponse({"error": f"Debug error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def create_stock(request):
    try:
        body = json.loads(request.body)
        
        # Updated validation to include GST
        required = ['name', 'quantity', 'defective', 'cost_per_unit', 'stock_limit', 'username', 'unit', 'group_id', 'gst']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        # Duplicate check - exact Lambda behavior
        item_id = body['name']
        existing = dynamodb_service.get_item('STOCK', {'item_id': item_id})
        if existing:
            return JsonResponse({"message": "already exist"}, status=400)

        # Parse inputs including GST
        quantity = Decimal(str(body['quantity']))
        defective = Decimal(str(body['defective']))
        cost_per_unit = Decimal(str(body['cost_per_unit']))
        stock_limit = Decimal(str(body['stock_limit']))
        gst_percentage = Decimal(str(body['gst']))
        username = body['username']
        unit = body['unit']
        group_id = body['group_id']

        # Validate GST percentage
        if gst_percentage < 0 or gst_percentage > 100:
            return JsonResponse({"error": "GST percentage must be between 0 and 100"}, status=400)

        # Compute derived values with GST
        available_qty = quantity - defective
        total_cost = available_qty * cost_per_unit
        gst_amount = (total_cost * gst_percentage) / Decimal('100')
        final_total_cost = total_cost + gst_amount
        now_iso = datetime.now().isoformat()

        # Persist with cost_per_unit unchanged and GST calculated separately
        stock_item = {
            'item_id': item_id,
            'name': item_id,
            'quantity': available_qty,
            'cost_per_unit': cost_per_unit,
            'gst_percentage': gst_percentage,
            'gst_amount': gst_amount,
            'total_cost': final_total_cost,
            'stock_limit': stock_limit,
            'defective': defective,
            'total_quantity': quantity,
            'unit': unit,
            'username': username,
            'group_id': group_id,
            'created_at': now_iso,
            'updated_at': now_iso
        }
        
        dynamodb_service.put_item('STOCK', stock_item)
        
        # Log transaction with GST details
        log_transaction("CreateStock", {
            'item_id': item_id,
            'available_qty': available_qty,
            'defective': defective,
            'total_qty': quantity,
            'cost_per_unit': cost_per_unit,
            'gst_percentage': gst_percentage,
            'gst_amount': gst_amount,
            'total_cost': final_total_cost,
            'stock_limit': stock_limit,
            'unit': unit,
            'group_id': group_id
        }, username)
        
        log_undo_action("CreateStock", {
            'item_id': item_id,
            'group_id': group_id
        }, username)
        
        recalc_all_production()
        logger.info(f"Stock created: {item_id}")
        
        # Return response with GST details
        return JsonResponse({
            "message": "Stock created successfully.",
            "item_id": item_id,
            "quantity": int(available_qty),
            "total_quantity": int(quantity),
            "cost_per_unit": float(cost_per_unit),
            "gst_percentage": float(gst_percentage),
            "gst_amount": float(gst_amount),
            "total_cost": float(final_total_cost),
            "stock_limit": float(stock_limit),
            "defective": int(defective),
            "unit": unit,
            "group_id": group_id
        })
        
    except Exception as e:
        logger.error(f"Error in create_stock: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["PUT"])
@jwt_required
def update_stock(request):
    try:
        body = json.loads(request.body)
        
        item_id = body.get('name')
        if not item_id:
            return JsonResponse({"error": "'name' is required"}, status=400)

        existing = dynamodb_service.get_item('STOCK', {'item_id': item_id})
        if not existing:
            return JsonResponse({"error": "Stock item not found"}, status=404)

        username = body.get('username')
        if not username:
            return JsonResponse({"error": "'username' is required"}, status=400)

        # Get current quantity for recalculation
        quantity = Decimal(str(existing.get('quantity', 0)))
        old_state = {}
        updated = False

        # Update GST%
        if 'gst' in body:
            new_gst = Decimal(str(body['gst']))
            if new_gst < 0 or new_gst > 100:
                return JsonResponse({"error": "GST percentage must be between 0 and 100"}, status=400)
            old_state['gst_percentage'] = existing.get('gst_percentage', 0)
            existing['gst_percentage'] = new_gst
            updated = True

        # Update COST_PER_UNIT
        if 'cost_per_unit' in body:
            old_state['cost_per_unit'] = existing.get('cost_per_unit', 0)
            existing['cost_per_unit'] = Decimal(str(body['cost_per_unit']))
            updated = True

        # Update UNIT
        if 'unit' in body:
            old_state['unit'] = existing.get('unit', '')
            existing['unit'] = body['unit']
            updated = True

        # Update STOCK_LIMIT
        if 'stock_limit' in body:
            old_state['stock_limit'] = existing.get('stock_limit', 0)
            existing['stock_limit'] = Decimal(str(body['stock_limit']))
            updated = True

        if not updated:
            return JsonResponse({"error": "No valid fields to update"}, status=400)

        # Recalculate total_cost with new values
        cost_per_unit = Decimal(str(existing.get('cost_per_unit', 0)))
        gst_percentage = Decimal(str(existing.get('gst_percentage', 0)))
        base_cost = quantity * cost_per_unit
        gst_amount = (base_cost * gst_percentage) / Decimal('100')
        total_cost = base_cost + gst_amount

        existing['gst_amount'] = gst_amount
        existing['total_cost'] = total_cost
        existing['updated_at'] = datetime.now().isoformat()

        dynamodb_service.put_item('STOCK', existing)

        log_transaction("UpdateStock", {
            'item_id': item_id,
            'old_values': {k: float(v) if isinstance(v, Decimal) else v for k, v in old_state.items()},
            'new_gst_percentage': float(gst_percentage),
            'new_cost_per_unit': float(cost_per_unit),
            'new_unit': existing.get('unit'),
            'new_stock_limit': float(existing.get('stock_limit', 0)),
            'recalculated_total_cost': float(total_cost)
        }, username)

        log_undo_action("UpdateStock", {'item_id': item_id, 'old_state': old_state}, username)
        recalc_all_production()

        return JsonResponse({
            "message": "Stock updated successfully",
            "item_id": item_id,
            "cost_per_unit": float(cost_per_unit),
            "gst_percentage": float(gst_percentage),
            "gst_amount": float(gst_amount),
            "total_cost": float(total_cost),
            "unit": existing.get('unit'),
            "stock_limit": float(existing.get('stock_limit', 0)),
            "quantity": float(quantity),
            "updated_at": existing['updated_at']
        })
        
    except Exception as e:
        logger.error(f"Error in update_stock: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
@admin_required
def delete_stock(request):
    try:
        body = json.loads(request.body)
        
        # Lambda uses 'name' and 'username'
        required = ['name', 'username']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        name = body['name']
        username = body['username']
        
        # Check if item exists
        existing = dynamodb_service.get_item('STOCK', {'item_id': name})
        if not existing:
            return JsonResponse({"error": f"Stock item '{name}' not found."}, status=404)
        
        deleted_item = existing.copy()
        
        # Delete the item
        dynamodb_service.delete_item('STOCK', {'item_id': name})
        
        log_transaction("DeleteStock", {"item_id": name, "details": f"Stock '{name}' deleted"}, username)
        log_undo_action("DeleteStock", {'deleted_item': deleted_item}, username)
        recalc_all_production()
        
        logger.info(f"Stock '{name}' deleted by {username}.")
        return JsonResponse({"message": f"Stock '{name}' deleted successfully."})
        
    except Exception as e:
        logger.error(f"Error in delete_stock: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@jwt_required
def get_all_stocks(request):
    try:
        group_id = request.GET.get('group_id')
        logger.info(f"Fetching stocks for group_id: {group_id}")
        
        # Get all groups first to build hierarchy
        all_groups = dynamodb_service.scan_table('GROUPS')
        groups_dict = {group['group_id']: group for group in all_groups}
        
        # Build group hierarchy helper function
        def get_child_groups(parent_id):
            children = []
            for group in all_groups:
                if group.get('parent_id') == parent_id:
                    children.append(group['group_id'])
                    children.extend(get_child_groups(group['group_id']))
            return children
        
        if group_id:
            # Get stocks for specific group and all its child groups
            target_groups = [group_id] + get_child_groups(group_id)
            
            # Get stocks for all target groups
            all_stocks = dynamodb_service.scan_table('STOCK')
            stocks = [stock for stock in all_stocks if stock.get('group_id') in target_groups]
        else:
            # Get all stocks
            stocks = dynamodb_service.scan_table('STOCK')
        
        # Build hierarchical tree structure
        from collections import defaultdict
        
        # Map parent_id -> list of child group_ids
        children = defaultdict(list)
        for group in all_groups:
            parent_id = group.get('parent_id')
            children[parent_id].append(group['group_id'])
        
        # Map group_id -> list of stock items
        items_by_group = defaultdict(list)
        for stock in stocks:
            group_id = stock.get('group_id')
            if group_id not in groups_dict:
                group_id = None
            items_by_group[group_id].append(stock)
        
        # Recursive tree builder
        def build_tree(parent_id):
            nodes = []
            for group_id in children.get(parent_id, []):
                group = groups_dict[group_id]
                node = {
                    "group_id": group_id,
                    "group_name": group['name'],
                    "items": items_by_group.get(group_id, []),
                    "subgroups": build_tree(group_id)
                }
                nodes.append(node)
            return nodes
        
        # Build tree starting from root groups
        tree = build_tree(None)
        
        # Add ungrouped items if any
        ungrouped = items_by_group.get(None, [])
        if ungrouped:
            tree.append({
                "group_id": None,
                "group_name": "null",
                "items": ungrouped,
                "subgroups": []
            })
        
        logger.info(f"Built hierarchical tree with {len(tree)} root groups")
        return JsonResponse(tree, safe=False)
        
    except Exception as e:
        logger.error(f"Error in get_all_stocks: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@jwt_required
def list_inventory_stock(request):
    try:
        # Get query parameters
        limit = int(request.GET.get('limit', 100))
        item_name = request.GET.get('item_name')
        
        logger.info(f"Fetching inventory stock - limit: {limit}, item_name: {item_name}")
        
        # Get all stocks first
        all_stocks = dynamodb_service.scan_table('STOCK')
        
        # Filter by item name if provided
        if item_name:
            stocks = [stock for stock in all_stocks 
                     if item_name.lower() in stock.get('name', '').lower()]
        else:
            stocks = all_stocks
        
        # Apply limit
        stocks = stocks[:limit]
        
        # Get groups for enhanced display
        all_groups = dynamodb_service.scan_table('GROUPS')
        groups_dict = {group['group_id']: group for group in all_groups}
        
        # Enhance inventory with group information
        enhanced_inventory = []
        for stock in stocks:
            enhanced_stock = stock.copy()
            stock_group_id = stock.get('group_id')
            if stock_group_id and stock_group_id in groups_dict:
                enhanced_stock['group_name'] = groups_dict[stock_group_id].get('name', 'Unknown')
            else:
                enhanced_stock['group_name'] = 'Uncategorized'
            
            # Calculate available quantity (total - defective)
            total_qty = int(enhanced_stock.get('total_quantity', 0))
            defective_qty = int(enhanced_stock.get('defective', 0))
            enhanced_stock['available_quantity'] = total_qty - defective_qty
            
            enhanced_inventory.append(enhanced_stock)
        
        # Sort by name for consistent ordering
        enhanced_inventory.sort(key=lambda x: x.get('name', '').lower())
        
        logger.info(f"Found {len(enhanced_inventory)} inventory items from DynamoDB")
        return JsonResponse({"inventory": enhanced_inventory}, safe=False)
        
    except Exception as e:
        logger.error(f"Error in list_inventory_stock: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def add_stock_quantity(request):
    try:
        body = json.loads(request.body)
        
        # Lambda uses 'name' and 'quantity_to_add'
        required = ['name', 'quantity_to_add', 'username', 'supplier_name']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        item_id = body['name']
        username = body['username']
        supplier_name = body['supplier_name']  # Mandatory field
        
        try:
            q_add = Decimal(str(body['quantity_to_add']))
            if q_add <= 0:
                raise ValueError
        except Exception:
            return JsonResponse({"error": "'quantity_to_add' must be > 0"}, status=400)
        
        # Get existing stock
        existing = dynamodb_service.get_item('STOCK', {'item_id': item_id})
        if not existing:
            return JsonResponse({"error": f"Stock item '{item_id}' not found."}, status=404)
        
        # Before values with GST
        before_available = Decimal(str(existing.get('quantity', 0)))
        before_defective = Decimal(str(existing.get('defective', 0)))
        before_total = before_available + before_defective
        before_total_cost = Decimal(str(existing.get('total_cost', 0)))
        cost_per_unit = Decimal(str(existing.get('cost_per_unit', 0)))
        gst_percentage = Decimal(str(existing.get('gst_percentage', 0)))

        # Compute after values with GST
        after_available = before_available + q_add
        after_total = after_available + before_defective
        base_added_cost = cost_per_unit * q_add
        gst_amount = (base_added_cost * gst_percentage) / Decimal('100')
        added_cost = base_added_cost + gst_amount
        after_total_cost = before_total_cost + added_cost
        now_ts = datetime.now().isoformat()

        # Update stock with GST
        existing.update({
            'quantity': after_available,
            'total_quantity': after_total,
            'gst_amount': Decimal(str(existing.get('gst_amount', 0))) + gst_amount,
            'total_cost': after_total_cost,
            'updated_at': now_ts
        })
        dynamodb_service.put_item('STOCK', existing)
        
        # Log with GST details
        transaction_data = {
            "item_id": item_id,
            "quantity_added": float(q_add),
            "cost_per_unit": float(cost_per_unit),
            "gst_percentage": float(gst_percentage),
            "gst_amount": float(gst_amount),
            "added_cost": float(added_cost),
            "before_available": float(before_available),
            "before_defective": float(before_defective),
            "before_total": float(before_total),
            "before_total_cost": float(before_total_cost),
            "after_available": float(after_available),
            "after_total": float(after_total),
            "after_total_cost": float(after_total_cost),
        }
        
        transaction_data["supplier_name"] = supplier_name
            
        log_transaction("AddStockQuantity", transaction_data, username)

        log_undo_action("AddStockQuantity", {
            "item_id": item_id,
            "quantity_added": float(q_add)
        }, username)

        recalc_all_production()
        
        return JsonResponse({
            "message": f"Added {float(q_add)} units to stock '{item_id}'.",
            "item_id": item_id,
            "quantity_added": float(q_add),
            "new_available": float(after_available),
            "new_total": float(after_total),
            "cost_per_unit": float(cost_per_unit),
            "gst_percentage": float(gst_percentage),
            "gst_amount": float(gst_amount),
            "added_cost": float(added_cost),
            "new_total_cost": float(after_total_cost),
            "supplier_name": supplier_name,
            "updated_at": now_ts
        })
        
    except Exception as e:
        logger.error(f"Error in add_stock_quantity: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def subtract_stock_quantity(request):
    try:
        body = json.loads(request.body)
        
        # Lambda uses 'name' and 'quantity_to_subtract'
        required = ['name', 'quantity_to_subtract', 'username']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        item_id = body['name']
        username = body['username']
        
        try:
            q_sub = Decimal(str(body['quantity_to_subtract']))
            if q_sub <= 0:
                raise ValueError
        except Exception:
            return JsonResponse({"error": "'quantity_to_subtract' must be > 0"}, status=400)
        
        # Get existing stock
        existing = dynamodb_service.get_item('STOCK', {'item_id': item_id})
        if not existing:
            return JsonResponse({"error": f"Stock item '{item_id}' not found."}, status=404)
        
        # Before values (exact Lambda logic)
        before_available = Decimal(str(existing.get('quantity', 0)))
        before_defective = Decimal(str(existing.get('defective', 0)))
        before_total = before_available + before_defective
        before_total_cost = Decimal(str(existing.get('total_cost', 0)))
        cost_per_unit = Decimal(str(existing.get('cost_per_unit', 0)))

        # Availability check (only available matters)
        if before_available < q_sub:
            return JsonResponse({
                "error": f"Insufficient available quantity. Have {float(before_available)}, need {float(q_sub)}."
            }, status=400)

        # Compute after values
        after_available = before_available - q_sub
        after_total = after_available + before_defective
        sub_cost = cost_per_unit * q_sub
        after_total_cost = before_total_cost - sub_cost
        if after_total_cost < 0:
            after_total_cost = Decimal("0")
        now_ts = datetime.now().isoformat()

        # Update stock
        existing.update({
            'quantity': after_available,
            'total_quantity': after_total,
            'total_cost': after_total_cost,
            'updated_at': now_ts
        })
        dynamodb_service.put_item('STOCK', existing)
        
        # Log exactly like Lambda
        log_transaction("SubtractStockQuantity", {
            "item_id": item_id,
            "quantity_subtracted": float(q_sub),
            "cost_per_unit": float(cost_per_unit),
            "subtracted_cost": float(sub_cost),
            "before_available": float(before_available),
            "before_defective": float(before_defective),
            "before_total": float(before_total),
            "before_total_cost": float(before_total_cost),
            "after_available": float(after_available),
            "after_total": float(after_total),
            "after_total_cost": float(after_total_cost),
        }, username)

        log_undo_action("SubtractStockQuantity", {
            "item_id": item_id,
            "quantity_subtracted": float(q_sub)
        }, username)

        recalc_all_production()
        
        return JsonResponse({
            "message": f"Subtracted {float(q_sub)} units from stock '{item_id}'.",
            "item_id": item_id,
            "quantity_subtracted": float(q_sub),
            "new_available": float(after_available),
            "new_total": float(after_total),
            "subtracted_cost": float(sub_cost),
            "new_total_cost": float(after_total_cost),
            "updated_at": now_ts
        })
        
    except Exception as e:
        logger.error(f"Error in subtract_stock_quantity: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def add_defective_goods(request):
    try:
        body = json.loads(request.body)
        
        # Lambda uses 'name' and 'defective_to_add'
        required = ['name', 'defective_to_add', 'username']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        name = body['name']
        defective_to_add = Decimal(str(body['defective_to_add']))
        username = body['username']
        
        # Get existing stock
        existing = dynamodb_service.get_item('STOCK', {'item_id': name})
        if not existing:
            return JsonResponse({"error": f"Stock item '{name}' not found."}, status=404)
        
        # Exact Lambda logic
        current_defective = Decimal(str(existing.get('defective', 0)))
        current_total = Decimal(str(existing.get('total_quantity', 0)))
        new_defective = current_defective + defective_to_add
        
        if new_defective > current_total:
            return JsonResponse({"error": "Defective count cannot exceed total quantity."}, status=400)
        
        new_available = current_total - new_defective
        now_str = datetime.now().isoformat()
        
        # Update stock
        existing.update({
            'defective': new_defective,
            'quantity': new_available,
            'updated_at': now_str
        })
        dynamodb_service.put_item('STOCK', existing)
        
        log_transaction("AddDefectiveGoods", {
            "item_id": name,
            "defective_added": defective_to_add,
            "new_defective": new_defective
        }, username)
        
        log_undo_action("AddDefectiveGoods", {
            "item_id": name, 
            "defective_added": defective_to_add
        }, username)
        
        recalc_all_production()
        
        return JsonResponse({
            "message": f"Added {defective_to_add} defective goods to stock '{name}'.",
            "item_id": name,
            "defective_added": float(defective_to_add),
            "new_defective": float(new_defective),
            "new_available": float(new_available)
        })
        
    except Exception as e:
        logger.error(f"Error in add_defective_goods: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def subtract_defective_goods(request):
    try:
        body = json.loads(request.body)
        
        # Lambda uses 'name' and 'defective_to_subtract'
        required = ['name', 'defective_to_subtract', 'username']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        name = body['name']
        defective_to_subtract = Decimal(str(body['defective_to_subtract']))
        username = body['username']
        
        # Get existing stock
        existing = dynamodb_service.get_item('STOCK', {'item_id': name})
        if not existing:
            return JsonResponse({"error": f"Stock item '{name}' not found."}, status=404)
        
        # Exact Lambda logic
        current_defective = Decimal(str(existing.get('defective', 0)))
        current_total = Decimal(str(existing.get('total_quantity', 0)))
        
        if current_defective < defective_to_subtract:
            return JsonResponse({
                "error": f"Insufficient defective quantity. Have {float(current_defective)}, need {float(defective_to_subtract)}."
            }, status=400)
        
        new_defective = current_defective - defective_to_subtract
        new_available = current_total - new_defective
        now_str = datetime.now().isoformat()
        
        # Update stock
        existing.update({
            'defective': new_defective,
            'quantity': new_available,
            'updated_at': now_str
        })
        dynamodb_service.put_item('STOCK', existing)
        
        log_transaction("SubtractDefectiveGoods", {
            "item_id": name,
            "defective_subtracted": defective_to_subtract,
            "new_defective": new_defective
        }, username)
        
        log_undo_action("SubtractDefectiveGoods", {
            "item_id": name, 
            "defective_subtracted": defective_to_subtract
        }, username)
        
        recalc_all_production()
        
        return JsonResponse({
            "message": f"Subtracted {defective_to_subtract} defective goods from stock '{name}'.",
            "item_id": name,
            "defective_subtracted": float(defective_to_subtract),
            "new_defective": float(new_defective),
            "new_available": float(new_available)
        })
        
    except Exception as e:
        logger.error(f"Error in subtract_defective_goods: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def create_description(request):
    try:
        body = json.loads(request.body)
        
        for field in ('stock', 'description', 'username'):
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        stock_item = {
            'stock': body['stock'],
            'description': body['description'],
            'username': body['username'],
            'created_at': datetime.now().isoformat()
        }
        
        dynamodb_service.put_item('stock_remarks', stock_item)
        
        return JsonResponse({"message": "Description saved successfully."})
        
    except Exception as e:
        logger.error(f"Error in create_description: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def get_description(request):
    try:
        body = json.loads(request.body)
        
        if 'stock' not in body:
            return JsonResponse({"error": "'stock' is required"}, status=400)
        
        stock_id = body['stock']
        
        # Get description from stock_remarks table
        item = dynamodb_service.get_item('stock_remarks', {'stock': stock_id})
        if not item:
            return JsonResponse({"error": f"No description found for stock '{stock_id}'"}, status=404)
        
        return JsonResponse({
            "stock": item['stock'],
            "description": item['description'],
            "username": item.get('username'),
            "created_at": item.get('created_at')
        })
        
    except Exception as e:
        logger.error(f"Error in get_description: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def get_all_descriptions(request):
    try:
        descriptions = dynamodb_service.scan_table('stock_remarks')
        logger.info(f"Found {len(descriptions)} descriptions from DynamoDB")
        return JsonResponse(descriptions, safe=False)
        
    except Exception as e:
        logger.error(f"Error in get_all_descriptions: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def save_opening_stock(request):
    try:
        body = json.loads(request.body)
        
        if 'username' not in body:
            return JsonResponse({"error": "'username' is required"}, status=400)
        
        username = body['username']
        
        # Fetch all stock items (exact Lambda logic)
        stocks = dynamodb_service.scan_table('STOCK')
        
        # Build per-item opening snapshot and compute aggregates
        per_item_opening = []
        aggregate_qty = Decimal('0')
        aggregate_amt = Decimal('0')
        
        for item in stocks:
            item_id = item.get('item_id')
            qty = Decimal(str(item.get('quantity', 0)))
            cpu = Decimal(str(item.get('cost_per_unit', 0)))
            amount = qty * cpu
            
            per_item_opening.append({
                "item_id": item_id,
                "opening_qty": int(qty),
                "opening_amount": amount
            })
            aggregate_qty += qty
            aggregate_amt += amount
        
        # Prepare transaction details (exact Lambda format)
        now_ist = datetime.now()
        timestamp_str = now_ist.isoformat()
        report_date = now_ist.strftime("%Y-%m-%d")
        
        details = {
            "aggregate_opening_qty": int(aggregate_qty),
            "aggregate_opening_amount": aggregate_amt,
            "per_item_opening": per_item_opening
        }
        
        # Check for existing opening stock record
        existing = get_existing_stock_record("SaveOpeningStock", report_date)
        
        if existing:
            # Update existing record
            existing['details'] = details
            existing['timestamp'] = timestamp_str
            existing['date'] = report_date
            dynamodb_service.put_item('stock_transactions', existing)
            logger.info(f"Updated opening stock transaction with ID: {existing['transaction_id']}")
            
            log_undo_action("SaveOpeningStock", details, username)
            logger.info(f"Updated opening stock for {username} on {report_date}")
            response_message = "Opening stock updated successfully."
        else:
            # Create new record with immediate verification
            transaction_id = str(uuid.uuid4())
            transaction_data = {
                'transaction_id': transaction_id,
                'operation_type': 'SaveOpeningStock',
                'date': report_date,
                'timestamp': timestamp_str,
                'username': username,
                'details': details
            }
            
            # Save to database with retry to ensure it's written
            max_save_attempts = 3
            for attempt in range(max_save_attempts):
                try:
                    dynamodb_service.put_item('stock_transactions', transaction_data)
                    logger.info(f"Saved opening stock transaction with ID: {transaction_id} on attempt {attempt + 1}")
                    break
                except Exception as e:
                    if attempt == max_save_attempts - 1:
                        raise e
                    logger.warning(f"Save attempt {attempt + 1} failed: {e}")
                    import time
                    time.sleep(0.5)
            
            log_undo_action("SaveOpeningStock", details, username)
            logger.info(f"Saved opening stock for {username} on {report_date}")
            response_message = "Opening stock saved successfully."
            
        # Verify the record was saved
        verification = get_existing_stock_record('SaveOpeningStock', report_date)
        if verification:
            logger.info(f"Verification successful: Opening stock record found with ID {verification.get('transaction_id')}")
        else:
            logger.error(f"Verification failed: Opening stock record not found for {report_date}")
            # Try direct verification
            try:
                all_trans = dynamodb_service.scan_table('stock_transactions')
                direct_check = [t for t in all_trans if t.get('operation_type') == 'SaveOpeningStock' and t.get('date') == report_date]
                logger.error(f"Direct check found {len(direct_check)} records for SaveOpeningStock on {report_date}")
            except Exception as ve:
                logger.error(f"Direct verification error: {ve}")
        
        return JsonResponse({
            "message": response_message,
            "report_date": report_date,
            "timestamp": timestamp_str,
            "aggregate_opening_qty": int(aggregate_qty),
            "aggregate_opening_amount": float(aggregate_amt),
            "per_item_opening": per_item_opening
        })
        
    except Exception as e:
        logger.error(f"Error in save_opening_stock: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def save_closing_stock(request):
    try:
        body = json.loads(request.body)
        
        if 'username' not in body:
            return JsonResponse({"error": "'username' is required"}, status=400)
        
        username = body['username']
        
        # Compute today's date & timestamp (exact Lambda logic)
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')
        ts = now.isoformat()
        
        # Check for opening stock with enhanced database search
        opening_record = None
        
        # Enhanced search with multiple attempts and strategies
        import time
        
        # Strategy 1: Direct function call
        opening_record = get_existing_stock_record('SaveOpeningStock', today)
        
        # Strategy 2: Manual scan if not found
        if not opening_record:
            try:
                logger.info(f"Direct search failed, trying manual scan for {today}")
                all_transactions = dynamodb_service.scan_table('stock_transactions')
                
                for transaction in all_transactions:
                    if (transaction.get('operation_type') == 'SaveOpeningStock' and 
                        transaction.get('date') == today):
                        opening_record = transaction
                        logger.info(f"Found opening stock via manual scan: {transaction.get('transaction_id')}")
                        break
            except Exception as e:
                logger.error(f"Manual scan failed: {e}")
        
        # Strategy 3: Retry after brief delay (for immediate saves)
        if not opening_record:
            logger.info("Retrying after delay...")
            time.sleep(2)
            opening_record = get_existing_stock_record('SaveOpeningStock', today)
            if opening_record:
                logger.info(f"Found opening stock on delayed retry")
        
        if not opening_record:
            return JsonResponse({
                'error': 'Opening stock must be saved before closing stock can be recorded',
                'details': f'No opening stock found for {today}. Please save opening stock first.'
            }, status=400)
        
        # Scan stock table for current quantities
        stocks = dynamodb_service.scan_table('STOCK')
        
        # Build per-item closing details + aggregates
        per_item = []
        agg_qty = Decimal('0')
        agg_amt = Decimal('0')
        
        for item in stocks:
            item_id = item['item_id']
            qty = Decimal(str(item.get('quantity', 0)))
            cpu = Decimal(str(item.get('cost_per_unit', 0)))
            amt = qty * cpu
            
            per_item.append({
                'item_id': item_id,
                'closing_qty': int(qty),
                'closing_amount': amt
            })
            agg_qty += qty
            agg_amt += amt
        
        details = {
            'aggregate_closing_qty': int(agg_qty),
            'aggregate_closing_amount': agg_amt,
            'per_item_closing': per_item
        }
        
        # Upsert into stock_transactions
        existing = get_existing_stock_record('SaveClosingStock', today)
        
        if existing:
            existing['details'] = details
            existing['timestamp'] = ts
            dynamodb_service.put_item('stock_transactions', existing)
            logger.info(f"Updated closing stock for {username} on {today}")
            msg = "Closing stock updated successfully."
        else:
            transaction_data = {
                'transaction_id': str(uuid.uuid4()),
                'operation_type': 'SaveClosingStock',
                'date': today,
                'timestamp': ts,
                'username': username,
                'details': details
            }
            dynamodb_service.put_item('stock_transactions', transaction_data)
            logger.info(f"Saved closing stock for {username} on {today}")
            msg = "Closing stock saved successfully."
        
        return JsonResponse({
            'message': msg,
            'date': today,
            'timestamp': ts,
            **details
        })
        
    except Exception as e:
        logger.error(f"Error in save_closing_stock: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def create_product(request):
    try:
        body = json.loads(request.body)
        
        # Required fields matching Lambda function
        required = [
            'product_name', 'stock_needed', 'username',
            'wastage_percent', 'transport_cost', 'labour_cost', 'other_cost'
        ]
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        # Parse inputs
        username = body['username']
        product_name = body['product_name']
        stock_needed = {k: Decimal(str(v)) for k, v in body['stock_needed'].items()}
        wastage_pct = Decimal(str(body['wastage_percent']))
        transport_cost = Decimal(str(body['transport_cost']))
        labour_cost = Decimal(str(body['labour_cost']))
        other_cost = Decimal(str(body['other_cost']))

        # Compute base_cost & max_produce
        stocks = dynamodb_service.scan_table('STOCK')
        stock_map = {item['item_id']: item for item in stocks}
        
        base_cost = Decimal('0')
        max_produce = None
        cost_breakdown = {}
        
        for item_id, qty_needed in stock_needed.items():
            if item_id not in stock_map:
                max_produce = Decimal('0')
                base_cost = Decimal('0')
                cost_breakdown = {}
                break
            
            stock_item = stock_map[item_id]
            available = Decimal(str(stock_item.get('quantity', 0)))
            possible = available // qty_needed if qty_needed > 0 else Decimal('0')
            max_produce = possible if max_produce is None else min(max_produce, possible)
            
            cpu = Decimal(str(stock_item.get('cost_per_unit', 0)))
            cost_item = cpu * qty_needed
            cost_breakdown[item_id] = cost_item
            base_cost += cost_item
        
        if max_produce is None:
            max_produce = Decimal('0')

        # Compute wastage & total cost
        wastage_amt = (base_cost * wastage_pct) / Decimal('100')
        total_cost = base_cost + wastage_amt + transport_cost + labour_cost + other_cost
        now_iso = datetime.now().isoformat()
        
        # Create product record
        product_id = str(uuid.uuid4())
        product_item = {
            'product_id': product_id,
            'product_name': product_name,
            'stock_needed': {k: str(v) for k, v in stock_needed.items()},
            'max_produce': int(max_produce),
            'original_max_produce': int(max_produce),
            'username': username,
            'production_cost_breakdown': {k: str(v) for k, v in cost_breakdown.items()},
            'production_cost_total': base_cost,
            'wastage_percent': wastage_pct,
            'wastage_amount': wastage_amt,
            'transport_cost': transport_cost,
            'labour_cost': labour_cost,
            'other_cost': other_cost,
            'total_cost': total_cost,
            'inventory': int(max_produce),
            'created_at': now_iso
        }
        
        dynamodb_service.put_item('PRODUCTION', product_item)
        
        # Log transaction and undo
        log_transaction("CreateProduct", {
            "product_id": product_id,
            "base_cost": base_cost,
            "wastage_pct": wastage_pct,
            "wastage_amt": wastage_amt,
            "transport_cost": transport_cost,
            "labour_cost": labour_cost,
            "other_cost": other_cost,
            "total_cost": total_cost
        }, username)
        
        log_undo_action("CreateProduct", {"product_id": product_id}, username)
        
        return JsonResponse({
            "message": "Product created successfully",
            "product_id": product_id,
            "production_cost_total": float(base_cost),
            "wastage_percent": float(wastage_pct),
            "wastage_amount": float(wastage_amt),
            "transport_cost": float(transport_cost),
            "labour_cost": float(labour_cost),
            "other_cost": float(other_cost),
            "total_cost": float(total_cost)
        })
        
    except Exception as e:
        logger.error(f"Error in create_product: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_product(request):
    try:
        body = json.loads(request.body)
        
        # Required fields matching lambda function
        if 'product_id' not in body or 'username' not in body:
            return JsonResponse({"error": "'product_id' and 'username' are required"}, status=400)
        
        product_id = body['product_id']
        username = body['username']
        
        # Check if product exists
        existing = dynamodb_service.get_item('PRODUCTION', {'product_id': product_id})
        if not existing:
            return JsonResponse({"error": "Product not found"}, status=404)
        
        # Load incoming or existing values, convert to Decimal
        raw_sn = body.get('stock_needed', existing.get('stock_needed', {}))
        stock_needed = {k: Decimal(str(v)) for k, v in raw_sn.items()}
        
        wastage_pct = Decimal(str(body.get('wastage_percent', existing.get('wastage_percent', 0))))
        transport_cost = Decimal(str(body.get('transport_cost', existing.get('transport_cost', 0))))
        labour_cost = Decimal(str(body.get('labour_cost', existing.get('labour_cost', 0))))
        other_cost = Decimal(str(body.get('other_cost', existing.get('other_cost', 0))))
        
        # Recalculate costs and production capacity
        base_cost = Decimal('0')
        max_prod = None
        cost_break = {}
        
        for item_id, qty_needed in stock_needed.items():
            stock_item = dynamodb_service.get_item('STOCK', {'item_id': item_id})
            if not stock_item:
                max_prod = Decimal('0')
                base_cost = Decimal('0')
                cost_break = {}
                break
            
            available = Decimal(str(stock_item.get('quantity', 0)))
            possible = available // qty_needed if qty_needed > 0 else Decimal('0')
            max_prod = possible if max_prod is None else min(max_prod, possible)
            
            cpu = Decimal(str(stock_item.get('cost_per_unit', 0)))
            ci = cpu * qty_needed
            cost_break[item_id] = ci
            base_cost += ci
        
        if max_prod is None:
            max_prod = Decimal('0')
        
        # Compute wastage and total cost
        wastage_amt = (base_cost * wastage_pct) / Decimal('100')
        total_cost = base_cost + wastage_amt + transport_cost + labour_cost + other_cost
        
        # Update timestamp
        now_iso = datetime.now().isoformat()
        
        # Update the product with all calculated values
        updated_item = existing.copy()
        updated_item.update({
            'stock_needed': {k: str(v) for k, v in stock_needed.items()},
            'wastage_percent': wastage_pct,
            'transport_cost': transport_cost,
            'labour_cost': labour_cost,
            'other_cost': other_cost,
            'max_produce': int(max_prod),
            'production_cost_breakdown': {k: str(v) for k, v in cost_break.items()},
            'production_cost_total': base_cost,
            'wastage_amount': wastage_amt,
            'total_cost': total_cost,
            'inventory': int(max_prod),
            'updated_at': now_iso
        })
        
        dynamodb_service.put_item('PRODUCTION', updated_item)
        
        # Log transaction
        log_transaction("UpdateProduct", {
            'product_id': product_id,
            'production_cost_total': total_cost,
            'wastage_amount': wastage_amt,
            'total_cost': total_cost
        }, username)
        
        log_undo_action("UpdateProduct", {
            'product_id': product_id,
            'old_state': existing
        }, username)
        
        return JsonResponse({
            "message": "Product updated successfully",
            "product_id": product_id,
            "total_cost": float(total_cost),
            "max_produce": int(max_prod)
        })
        
    except Exception as e:
        logger.error(f"Error in update_product: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def update_product_details(request):
    try:
        body = json.loads(request.body)
        
        required = ['product_id', 'username']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        product_id = body['product_id']
        username = body['username']
        
        # Check if product exists
        existing = dynamodb_service.get_item('PRODUCTION', {'product_id': product_id})
        if not existing:
            return JsonResponse({"error": "Product not found"}, status=404)
        
        # Update details like costs, wastage, etc.
        update_parts = []
        expression_values = {}
        
        for field in ['labour_cost', 'transport_cost', 'other_cost', 'wastage_percent']:
            if field in body:
                update_parts.append(f'{field} = :{field[:2]}')
                expression_values[f':{field[:2]}'] = Decimal(str(body[field]))
        
        if update_parts:
            update_expression = 'SET ' + ', '.join(update_parts)
            dynamodb_service.update_item(
                'PRODUCTION',
                {'product_id': product_id},
                update_expression,
                expression_values
            )
        
        return JsonResponse({"message": "Product details updated successfully", "product_id": product_id})
        
    except Exception as e:
        logger.error(f"Error in update_product_details: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
@admin_required
def delete_product(request):
    try:
        body = json.loads(request.body)
        
        if 'product_id' not in body:
            return JsonResponse({"error": "'product_id' is required"}, status=400)

        product_id = body['product_id']
        
        # Check if product exists
        existing = dynamodb_service.get_item('PRODUCTION', {'product_id': product_id})
        if not existing:
            return JsonResponse({"error": "Product not found"}, status=404)
        
        # Delete the product
        dynamodb_service.delete_item('PRODUCTION', {'product_id': product_id})
        
        return JsonResponse({"message": "Product deleted successfully", "product_id": product_id})
        
    except Exception as e:
        logger.error(f"Error in delete_product: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def get_all_products(request):
    try:
        products = dynamodb_service.scan_table('PRODUCTION')
        stocks = dynamodb_service.scan_table('STOCK')
        groups = dynamodb_service.scan_table('GROUPS')
        
        # Build stock and group maps
        stock_map = {item['item_id']: item for item in stocks}
        groups_by_id = {g['group_id']: {'name': g['name'], 'parent_id': g.get('parent_id')} for g in groups}
        
        # Cache for group chains
        chain_cache = {}
        def build_chain(gid):
            if gid in chain_cache:
                return chain_cache[gid]
            chain = []
            current = gid
            while current and current in groups_by_id:
                grp = groups_by_id[current]
                chain.insert(0, grp['name'])
                current = grp.get('parent_id')
            chain_cache[gid] = chain
            return chain
        
        # Enrich products
        enriched = []
        for p in products:
            details = []
            for mat_id, qty_str in p.get('stock_needed', {}).items():
                try:
                    qty = float(qty_str)
                except:
                    qty = float(Decimal(str(qty_str)))
                stock_item = stock_map.get(mat_id, {})
                group_id = stock_item.get('group_id')
                chain = build_chain(group_id) if group_id else []
                details.append({
                    'item_id': mat_id,
                    'required_qty': qty,
                    'group_chain': chain
                })
            p['stock_details'] = details
            p.pop('stock_needed', None)
            enriched.append(p)
        
        return JsonResponse(enriched, safe=False)
        
    except Exception as e:
        logger.error(f"Error in get_all_products: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@jwt_required
def debug_stock_items(request):
    """Debug endpoint to check stock items"""
    try:
        # Get specific item if provided
        item_id = request.GET.get('item_id')
        if item_id:
            stock_item = dynamodb_service.get_item('STOCK', {'item_id': item_id})
            return JsonResponse({
                "item_id": item_id,
                "found": stock_item is not None,
                "item": stock_item
            })
        
        # Get all stock items
        all_stocks = dynamodb_service.scan_table('STOCK')
        stock_summary = [{
            "item_id": item.get('item_id'),
            "name": item.get('name'),
            "quantity": item.get('quantity')
        } for item in all_stocks[:20]]  # Limit to first 20
        
        return JsonResponse({
            "total_count": len(all_stocks),
            "sample_items": stock_summary
        })
        
    except Exception as e:
        logger.error(f"Error in debug_stock_items: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def alter_product_components(request):
    try:
        body = json.loads(request.body)
        
        # Required fields
        missing = [f for f in ("product_id", "username") if f not in body]
        if missing:
            return JsonResponse({
                "error": f"Missing required field(s): {', '.join(missing)}"
            }, status=400)

        product_id = body["product_id"]
        username   = body["username"]
        to_delete  = body.get("stock_delete", [])
        to_add_map = body.get("stock_add", {})

        # Get product
        existing = dynamodb_service.get_item('PRODUCTION', {'product_id': product_id})
        if not existing:
            return JsonResponse({
                "error": f"Product '{product_id}' not found."
            }, status=404)

        # Check if materials exist in stock table
        all_stocks = None
        stock_map = None
        
        for mat_id in to_add_map:
            # Clean the material ID (remove whitespace)
            clean_mat_id = str(mat_id).strip()
            
            # Try direct lookup first
            stock_item = dynamodb_service.get_item('STOCK', {'item_id': clean_mat_id})
            
            if not stock_item:
                # If direct lookup fails, scan all items (lazy load)
                if stock_map is None:
                    try:
                        all_stocks = dynamodb_service.scan_table('STOCK')
                        stock_map = {item.get('item_id', '').strip(): item for item in all_stocks}
                        logger.info(f"Loaded {len(stock_map)} stock items for validation")
                    except Exception as e:
                        logger.error(f"Failed to load stock items: {e}")
                        return JsonResponse({
                            "error": f"Cannot validate materials: database error"
                        }, status=500)
                
                # Try case-insensitive lookup
                stock_item = stock_map.get(clean_mat_id)
                if not stock_item:
                    # Try case-insensitive search
                    for stock_id, item in stock_map.items():
                        if stock_id.lower() == clean_mat_id.lower():
                            stock_item = item
                            break
                
                if not stock_item:
                    available_ids = list(stock_map.keys())[:10]
                    logger.error(f"Material '{clean_mat_id}' not found. Available IDs: {available_ids}...")
                    
                    return JsonResponse({
                        "error": f"Cannot add '{clean_mat_id}': not found in stock table.",
                        "available_items": available_ids
                    }, status=400)

        # Parse existing stock_needed
        raw_stock_map = existing.get("stock_needed", {})
        current_map = {}
        for mat_id, qty_val in raw_stock_map.items():
            try:
                current_map[mat_id] = float(qty_val)
            except (ValueError, TypeError):
                try:
                    current_map[mat_id] = float(Decimal(str(qty_val)))
                except:
                    current_map[mat_id] = 0.0

        original_map = current_map.copy()

        # Delete materials
        for mat_id in to_delete:
            current_map.pop(mat_id, None)

        # Add/update materials (use original mat_id to preserve exact keys)
        for mat_id, qty in to_add_map.items():
            try:
                q = float(qty)
                if q <= 0:
                    raise ValueError()
                current_map[mat_id] = q
            except:
                return JsonResponse({
                    "error": f"Invalid quantity for '{mat_id}': must be a positive number."
                }, status=400)

        # Filter out ≤0
        current_map = {k: v for k, v in current_map.items() if v > 0}

        # If no change, return early
        if current_map == original_map:
            return JsonResponse({"message": "No changes to apply."})

        # Convert costs to float safely
        def to_float(x):
            try:
                return float(x)
            except:
                try:
                    return float(Decimal(str(x)))
                except:
                    return 0.0

        # Call update_product to recalculate everything
        from django.http import HttpRequest
        update_request = HttpRequest()
        update_request.method = 'POST'
        update_body = {
            "product_id":      product_id,
            "username":        username,
            "stock_needed":    current_map,
            "wastage_percent": to_float(existing.get("wastage_percent", 0)),
            "transport_cost":  to_float(existing.get("transport_cost",   0)),
            "labour_cost":     to_float(existing.get("labour_cost",     0)),
            "other_cost":      to_float(existing.get("other_cost",      0)),
        }
        update_request._body = json.dumps(update_body).encode('utf-8')
        
        response = update_product(update_request)

        # Log the change
        change_log = {
            "product_id":   product_id,
            "stock_delete": to_delete,
            "stock_add":    to_add_map
        }
        log_transaction("AlterProductComponents", change_log, username)
        log_undo_action("AlterProductComponents", change_log, username)

        return response
        
    except Exception as e:
        logger.error(f"Error in alter_product_components: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def push_to_production(request):
    try:
        body = json.loads(request.body)
        
        required = ['product_id', 'quantity', 'username']
        missing = [f for f in required if f not in body]
        if missing:
            return JsonResponse({"error": f"Missing required field(s): {', '.join(missing)}"}, status=400)

        product_id = body['product_id']
        quantity_to_produce = Decimal(str(body['quantity']))
        username = body['username']
        provided_cost_per_unit = body.get('production_cost_per_unit')
        
        if quantity_to_produce <= 0:
            return JsonResponse({"error": "quantity must be > 0"}, status=400)
            
        # Get product
        products = dynamodb_service.scan_table('PRODUCTION')
        product_item = None
        for product in products:
            if product.get('product_id') == product_id:
                product_item = product
                break
                
        if not product_item:
            return JsonResponse({"error": f"Product '{product_id}' not found"}, status=404)
            
        product_name = product_item.get('product_name', product_id)
        stock_needed = product_item.get('stock_needed', {})
        
        if not stock_needed:
            return JsonResponse({"error": "Product has no 'stock_needed' defined"}, status=400)
            
        # Check stock availability
        stock_items = dynamodb_service.scan_table('STOCK')
        stock_map = {item['item_id']: item for item in stock_items}
        
        required_deductions = {}
        cost_per_unit_total = Decimal(str(provided_cost_per_unit)) if provided_cost_per_unit else Decimal('0')
        
        for item_id, qty_each in stock_needed.items():
            qty_each_dec = Decimal(str(qty_each))
            total_needed = qty_each_dec * quantity_to_produce
            
            if item_id not in stock_map:
                return JsonResponse({"error": f"Required stock '{item_id}' not found"}, status=400)
                
            stock_item = stock_map[item_id]
            available = Decimal(str(stock_item.get('quantity', 0)))
            cpu = Decimal(str(stock_item.get('cost_per_unit', 0)))
            
            if available < total_needed:
                return JsonResponse({
                    "error": f"Insufficient stock '{item_id}' to produce {float(quantity_to_produce)}",
                    "available": float(available),
                    "required": float(total_needed)
                }, status=400)
                
            required_deductions[item_id] = total_needed
            if not provided_cost_per_unit:
                cost_per_unit_total += (cpu * qty_each_dec)
            
        # Apply deductions
        now_ist = datetime.now().isoformat()
        for item_id, deduct_qty in required_deductions.items():
            stock_item = stock_map[item_id]
            current_qty = Decimal(str(stock_item.get('quantity', 0)))
            defective = Decimal(str(stock_item.get('defective', 0)))
            cpu = Decimal(str(stock_item.get('cost_per_unit', 0)))
            total_cost = Decimal(str(stock_item.get('total_cost', 0)))
            
            new_available = current_qty - deduct_qty
            new_total = new_available + defective
            new_total_cost = total_cost - (cpu * deduct_qty)
            if new_total_cost < 0:
                new_total_cost = Decimal('0')
                
            stock_item.update({
                'quantity': new_available,
                'total_quantity': new_total,
                'total_cost': new_total_cost,
                'updated_at': now_ist
            })
            dynamodb_service.put_item('STOCK', stock_item)
            
        # Create push record
        push_id = str(uuid.uuid4())
        total_production_cost = cost_per_unit_total * quantity_to_produce
        
        push_record = {
            'push_id': push_id,
            'product_id': product_id,
            'product_name': product_name,
            'quantity_produced': quantity_to_produce,
            'stock_deductions': {k: v for k, v in required_deductions.items()},
            'status': 'ACTIVE',
            'username': username,
            'production_cost_per_unit': cost_per_unit_total,
            'total_production_cost': total_production_cost,
            'timestamp': now_ist
        }
        
        dynamodb_service.put_item('PUSH_TO_PRODUCTION', push_record)
        log_transaction("PushToProduction", {
            "push_id": push_id,
            "product_id": product_id,
            "product_name": product_name,
            "quantity_produced": float(quantity_to_produce),
            "deductions": {k: float(v) for k, v in required_deductions.items()}
        }, username)
        
        return JsonResponse({
            "message": "Product pushed to production successfully",
            "push_id": push_id,
            "product_id": product_id,
            "product_name": product_name,
            "quantity_produced": float(quantity_to_produce),
            "production_cost_per_unit": float(cost_per_unit_total),
            "total_production_cost": float(total_production_cost),
            "stock_deductions": {k: float(v) for k, v in required_deductions.items()}
        })
        
    except Exception as e:
        logger.error(f"Error in push_to_production: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
@admin_required
def undo_production(request):
    try:
        body = json.loads(request.body)
        
        required = ['push_id', 'username']
        missing = [f for f in required if f not in body]
        if missing:
            return JsonResponse({"error": f"Missing required field(s): {', '.join(missing)}"}, status=400)

        push_id = body['push_id']
        username = body['username']
        
        # Get push record
        push_records = dynamodb_service.scan_table('PUSH_TO_PRODUCTION')
        push_item = None
        for record in push_records:
            if record.get('push_id') == push_id:
                push_item = record
                break
                
        if not push_item:
            return JsonResponse({"error": f"Push '{push_id}' not found"}, status=404)
            
        if push_item.get('status') != 'ACTIVE':
            return JsonResponse({"error": f"Push '{push_id}' is not active or already undone"}, status=400)
            
        # Restore stock quantities
        stock_deductions = push_item.get('stock_deductions', {})
        stock_items = dynamodb_service.scan_table('STOCK')
        stock_map = {item['item_id']: item for item in stock_items}
        
        for item_id, deduction in stock_deductions.items():
            if item_id in stock_map:
                stock_item = stock_map[item_id]
                current_qty = Decimal(str(stock_item.get('quantity', 0)))
                defective = Decimal(str(stock_item.get('defective', 0)))
                cpu = Decimal(str(stock_item.get('cost_per_unit', 0)))
                total_cost = Decimal(str(stock_item.get('total_cost', 0)))
                
                new_qty = current_qty + Decimal(str(deduction))
                new_total = new_qty + defective
                new_total_cost = total_cost + (cpu * Decimal(str(deduction)))
                
                stock_item.update({
                    'quantity': new_qty,
                    'total_quantity': new_total,
                    'total_cost': new_total_cost,
                    'updated_at': datetime.now().isoformat()
                })
                dynamodb_service.put_item('STOCK', stock_item)
                
        # Mark push as undone
        push_item['status'] = 'UNDONE'
        push_item['undone_at'] = datetime.now().isoformat()
        push_item['undone_by'] = username
        dynamodb_service.put_item('PUSH_TO_PRODUCTION', push_item)
        
        log_transaction("UndoProduction", {
            "push_id": push_id,
            "details": f"Stock restored for push '{push_id}'"
        }, username)
        
        return JsonResponse({
            "message": f"Push '{push_id}' undone successfully"
        })
        
    except Exception as e:
        logger.error(f"Error in undo_production: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
@admin_required
def delete_push_to_production(request):
    try:
        body = json.loads(request.body)
        
        required = ['push_id', 'username']
        missing = [f for f in required if f not in body]
        if missing:
            return JsonResponse({"error": f"Missing required field(s): {', '.join(missing)}"}, status=400)

        push_id = body['push_id']
        username = body['username']
        
        # Check if push record exists
        push_records = dynamodb_service.scan_table('PUSH_TO_PRODUCTION')
        push_exists = any(record.get('push_id') == push_id for record in push_records)
        
        if not push_exists:
            return JsonResponse({"error": f"Push record '{push_id}' not found"}, status=404)
            
        # Delete push record
        dynamodb_service.delete_item('PUSH_TO_PRODUCTION', {'push_id': push_id})
        log_transaction("DeletePushToProduction", {
            "push_id": push_id,
            "details": f"Push record '{push_id}' deleted"
        }, username)
        
        return JsonResponse({
            "message": f"Push record '{push_id}' deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error in delete_push_to_production: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
@admin_required
def undo_action(request):
    try:
        body = json.loads(request.body)
        
        required = ['undo_id', 'username']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        undo_id = body['undo_id']
        username = body['username']
        
        # Check if undo record exists
        undo_record = dynamodb_service.get_item('undo_actions', {'undo_id': undo_id})
        if not undo_record:
            return JsonResponse({"error": "Undo record not found"}, status=404)
        
        # Restore original data based on action type
        action = undo_record.get('action')
        original_data = undo_record.get('original_data')
        
        if action == 'undo_production' and original_data:
            # Restore the push record
            dynamodb_service.put_item('push_to_production', original_data)
        
        # Delete the undo record
        dynamodb_service.delete_item('undo_actions', {'undo_id': undo_id})
        
        return JsonResponse({"message": "Action undone successfully", "action": action})
        
    except Exception as e:
        logger.error(f"Error in undo_action: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
@admin_required
def delete_transaction_data(request):
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
        tables_to_clear = ['stock_transactions', 'undo_actions', 'push_to_production']
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
                    elif table_name == 'push_to_production':
                        key = {'push_id': item['push_id']}
                    
                    dynamodb_service.delete_item(table_name, key)
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"Error clearing {table_name}: {e}")
        
        return JsonResponse({"message": "Transaction data deleted successfully", "deleted_count": deleted_count})
        
    except Exception as e:
        logger.error(f"Error in delete_transaction_data: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def test_stock_lookup(request):
    """Test endpoint to verify stock lookup functionality"""
    try:
        body = json.loads(request.body)
        item_id = body.get('item_id')
        
        if not item_id:
            return JsonResponse({"error": "'item_id' is required"}, status=400)
        
        # Test the lookup
        stock_item = dynamodb_service.get_item('STOCK', {'item_id': item_id})
        
        return JsonResponse({
            "item_id": item_id,
            "found": stock_item is not None,
            "item": stock_item
        })
        
    except Exception as e:
        logger.error(f"Error in test_stock_lookup: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

# Lambda-style functions for operation routing
@csrf_exempt
@jwt_required
def creategroup(request, body):
    try:
        if 'name' not in body:
            return JsonResponse({"error": "'name' is required"}, status=400)

        name = body['name']
        parent_id = body.get('parent_id')  # may be None
        group_id = str(uuid.uuid4())

        # Create group in DynamoDB
        group_item = {
            'group_id': group_id,
            'name': name
        }
        if parent_id:
            group_item['parent_id'] = parent_id
        
        dynamodb_service.put_item('GROUPS', group_item)
        
        logger.info(f"Group created: {group_id} ('{name}', parent={parent_id})")

        return JsonResponse({
            "message": "Group created successfully",
            "group_id": group_id,
            "name": name,
            "parent_id": parent_id
        })
        
    except Exception as e:
        logger.error(f"Error in creategroup: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@jwt_required
def listgroups(request, body=None):
    # Handle both direct calls and lambda-style calls
    if body is None:
        try:
            body = json.loads(request.body) if request.body else {}
        except:
            body = {}
    try:
        parent_id = body.get('parent_id')
        logger.info(f"Fetching groups with parent_id: {parent_id}")
        
        try:
            if parent_id:
                # Query groups with specific parent_id
                groups = dynamodb_service.scan_table(
                    'GROUPS', 
                    FilterExpression='parent_id = :pid', 
                    ExpressionAttributeValues={':pid': parent_id}
                )
            else:
                # Get root groups (no parent_id)
                groups = dynamodb_service.scan_table(
                    'GROUPS', 
                    FilterExpression='attribute_not_exists(parent_id)'
                )
            
            logger.info(f"Found {len(groups)} groups")
            return JsonResponse(groups, safe=False)
            
        except ClientError as e:
            logger.error(f"DynamoDB error fetching groups: {e}")
            return JsonResponse({"error": "Failed to fetch groups from database"}, status=500)
        
    except Exception as e:
        logger.error(f"Error in listgroups: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@jwt_required
def deletegroup(request, body):
    try:
        if 'group_id' not in body:
            return JsonResponse({"error": "'group_id' is required"}, status=400)

        group_id = body['group_id']
        
        # Check if group exists
        existing = dynamodb_service.get_item('GROUPS', {'group_id': group_id})
        if not existing:
            return JsonResponse({"error": "Group not found"}, status=404)
        
        # Delete the group
        dynamodb_service.delete_item('GROUPS', {'group_id': group_id})
        
        logger.info(f"Group deleted: {group_id}")
        return JsonResponse({
            "message": "Group deleted successfully",
            "group_id": group_id
        })
        
    except Exception as e:
        logger.error(f"Error in deletegroup: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)