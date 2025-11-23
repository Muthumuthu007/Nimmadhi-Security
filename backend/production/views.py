import json
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from users.decorators import jwt_required, admin_required
import logging

logger = logging.getLogger(__name__)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

# Helper functions for production operations
def log_transaction(action, data, username):
    try:
        from backend.dynamodb_service import dynamodb_service
        transaction_id = str(uuid.uuid4())
        ts = datetime.now().isoformat()
        date_str = ts.split("T")[0]
        
        transaction_data = {
            'transaction_id': transaction_id,
            'operation_type': action,
            'details': data,
            'date': date_str,
            'timestamp': ts,
            'username': username
        }
        dynamodb_service.put_item('stock_transactions', transaction_data)
        logger.info(f"Transaction logged: {action} by {username}")
    except Exception as e:
        logger.error(f"Error logging transaction: {e}")

def log_undo_action(action, data, username):
    try:
        from backend.dynamodb_service import dynamodb_service
        undo_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        undo_data = {
            'undo_id': undo_id,
            'operation': action,
            'undo_details': data,
            'username': username,
            'status': 'ACTIVE',
            'timestamp': timestamp
        }
        dynamodb_service.put_item('undo_actions', undo_data)
        logger.info(f"Undo action logged: {action} by {username}")
    except Exception as e:
        logger.error(f"Error logging undo action: {e}")

def recalc_max_produce(product_id):
    logger.info(f"Recalculating max produce for {product_id}")

def get_group_chain(group_id):
    return []

@csrf_exempt
@jwt_required
def create_product(request):
    try:
        from backend.dynamodb_service import dynamodb_service
        
        body = json.loads(request.body)
        
        required = ['product_name', 'stock_needed', 'username', 'labour_cost', 'transport_cost', 'other_cost', 'wastage_percent']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        product_id = str(uuid.uuid4())
        product_name = body['product_name']
        stock_needed = body['stock_needed']
        username = body['username']
        labour_cost = Decimal(str(body['labour_cost']))
        transport_cost = Decimal(str(body['transport_cost']))
        other_cost = Decimal(str(body['other_cost']))
        wastage_percent = Decimal(str(body['wastage_percent']))
        
        # Check if product already exists
        existing_products = dynamodb_service.scan_table('PRODUCTION')
        for product in existing_products:
            if product.get('product_name') == product_name:
                return JsonResponse({"error": "Product already exists"}, status=400)

        # Calculate costs
        production_cost_total = labour_cost + transport_cost + other_cost
        total_cost = production_cost_total
        wastage_amount = total_cost * (wastage_percent / 100)
        
        product_item = {
            'product_id': product_id,
            'product_name': product_name,
            'stock_needed': stock_needed,
            'username': username,
            'labour_cost': labour_cost,
            'transport_cost': transport_cost,
            'other_cost': other_cost,
            'wastage_percent': wastage_percent,
            'wastage_amount': wastage_amount,
            'production_cost_total': production_cost_total,
            'total_cost': total_cost,
            'created_at': datetime.now().isoformat()
        }
        
        dynamodb_service.put_item('PRODUCTION', product_item)
        logger.info(f"Product created: {product_id} - {product_name}")
        
        return JsonResponse({
            "message": "Product created successfully",
            "product_id": product_id,
            "product_name": product_name
        })
        
    except Exception as e:
        logger.error(f"Error in create_product: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@jwt_required
def alter_product_components(request):
    try:
        from backend.dynamodb_service import dynamodb_service
        
        body = json.loads(request.body)
        
        required = ['product_id', 'username']
        missing = [f for f in required if f not in body]
        if missing:
            return JsonResponse({"error": f"Missing required field(s): {', '.join(missing)}"}, status=400)

        product_id = body['product_id']
        username = body['username']
        to_delete = body.get('stock_delete', [])
        to_add_map = body.get('stock_add', {})
        
        # Get existing product
        products = dynamodb_service.scan_table('PRODUCTION')
        existing = None
        for product in products:
            if product.get('product_id') == product_id:
                existing = product
                break
                
        if not existing:
            return JsonResponse({"error": f"Product '{product_id}' not found"}, status=404)
            
        # Validate materials exist in stock
        stock_items = dynamodb_service.scan_table('STOCK')
        stock_ids = {item['item_id'] for item in stock_items}
        
        for mat_id in to_add_map:
            if mat_id not in stock_ids:
                return JsonResponse({"error": f"Cannot add '{mat_id}': not found in stock table"}, status=400)
        
        # Parse existing stock_needed
        current_map = existing.get('stock_needed', {})
        original_map = current_map.copy()
        
        # Delete materials
        for mat_id in to_delete:
            current_map.pop(mat_id, None)
            
        # Add/update materials
        for mat_id, qty in to_add_map.items():
            try:
                q = float(qty)
                if q <= 0:
                    raise ValueError()
                current_map[mat_id] = q
            except:
                return JsonResponse({"error": f"Invalid quantity for '{mat_id}': must be a positive number"}, status=400)
        
        # Filter out ≤0
        current_map = {k: v for k, v in current_map.items() if v > 0}
        
        if current_map == original_map:
            return JsonResponse({"message": "No changes to apply"})
            
        # Update product with new stock_needed
        existing['stock_needed'] = current_map
        existing['updated_at'] = datetime.now().isoformat()
        
        dynamodb_service.put_item('PRODUCTION', existing)
        log_transaction("AlterProductComponents", {
            "product_id": product_id,
            "stock_delete": to_delete,
            "stock_add": to_add_map
        }, username)
        
        return JsonResponse({
            "message": "Product components altered successfully",
            "product_id": product_id,
            "stock_needed": current_map
        })
        
    except Exception as e:
        logger.error(f"Error in alter_product_components: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@jwt_required
def update_product_details(request):
    try:
        from backend.dynamodb_service import dynamodb_service
        
        body = json.loads(request.body)
        
        required = ['product_id', 'username']
        missing = [f for f in required if f not in body]
        if missing:
            return JsonResponse({"error": f"Missing required field(s): {', '.join(missing)}"}, status=400)

        product_id = body['product_id']
        username = body['username']
        
        # Get existing product
        products = dynamodb_service.scan_table('PRODUCTION')
        existing = None
        for product in products:
            if product.get('product_id') == product_id:
                existing = product
                break
                
        if not existing:
            return JsonResponse({"error": "Product not found"}, status=404)
            
        # Collect updatable fields
        updatables = {}
        for field in ['wastage_percent', 'transport_cost', 'labour_cost', 'other_cost']:
            if field in body:
                try:
                    updatables[field] = Decimal(str(body[field]))
                except:
                    return JsonResponse({"error": f"Invalid value for '{field}'"}, status=400)
        
        if not updatables:
            return JsonResponse({"error": "You must provide at least one of wastage_percent, transport_cost, labour_cost, other_cost"}, status=400)
            
        # Update product
        for field, value in updatables.items():
            existing[field] = value
        existing['updated_at'] = datetime.now().isoformat()
        
        dynamodb_service.put_item('PRODUCTION', existing)
        log_transaction("UpdateProductDetails", {
            "product_id": product_id,
            **{k: float(v) for k, v in updatables.items()}
        }, username)
        
        return JsonResponse({
            "message": "Product cost details updated",
            "product_id": product_id,
            **{k: float(v) for k, v in updatables.items()},
            "updated_at": existing['updated_at']
        }, cls=DecimalEncoder)
        
    except Exception as e:
        logger.error(f"Error in update_product_details: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@jwt_required
def get_monthly_push_to_production(request):
    try:
        from backend.dynamodb_service import dynamodb_service
        from collections import defaultdict
        from datetime import datetime
        
        body = json.loads(request.body) if request.body else {}
        username = body.get('username', 'Unknown')
        from_str = body.get('from_date')
        to_str = body.get('to_date')
        
        if not from_str or not to_str:
            return JsonResponse({"error": "'from_date' and 'to_date' are required (format: YYYY-MM-DD)"}, status=400)
            
        from_date = datetime.strptime(from_str, "%Y-%m-%d").date()
        to_date = datetime.strptime(to_str, "%Y-%m-%d").date()
        
        # Get all push records
        push_records = dynamodb_service.scan_table('PUSH_TO_PRODUCTION')
        
        # Filter by date range
        monthly_items = []
        for item in push_records:
            timestamp = item.get('timestamp')
            if timestamp:
                dt = datetime.strptime(timestamp[:10], "%Y-%m-%d").date()
                if from_date <= dt <= to_date:
                    monthly_items.append(item)
                    
        # Group by product for summary
        product_summary = defaultdict(lambda: {"product_name": "", "total_quantity": 0})
        
        for item in monthly_items:
            product_id = item.get('product_id', 'Unknown')
            product_name = item.get('product_name', 'Unknown')
            quantity = float(item.get('quantity_produced', 0))
            
            product_summary[product_id]["product_name"] = product_name
            product_summary[product_id]["total_quantity"] += quantity
            
        # Convert to list
        summary_list = [
            {
                "product_id": product_id,
                "product_name": data["product_name"],
                "total_quantity": data["total_quantity"]
            }
            for product_id, data in product_summary.items()
        ]
        
        return JsonResponse({
            "summary": summary_list,
            "items": monthly_items
        }, cls=DecimalEncoder)
        
    except Exception as e:
        logger.error(f"Error in get_monthly_push_to_production: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@jwt_required
def update_product(request):
    try:
        from backend.dynamodb_service import dynamodb_service
        
        body = json.loads(request.body)
        
        required = ['product_id', 'username']
        missing = [f for f in required if f not in body]
        if missing:
            return JsonResponse({"error": f"Missing required field(s): {', '.join(missing)}"}, status=400)

        product_id = body['product_id']
        username = body['username']
        
        # Get existing product
        products = dynamodb_service.scan_table('PRODUCTION')
        existing = None
        for product in products:
            if product.get('product_id') == product_id:
                existing = product
                break
                
        if not existing:
            return JsonResponse({"error": "Product not found"}, status=404)
            
        # Load values from body or existing
        stock_needed = body.get('stock_needed', existing.get('stock_needed', {}))
        wastage_percent = Decimal(str(body.get('wastage_percent', existing.get('wastage_percent', 0))))
        transport_cost = Decimal(str(body.get('transport_cost', existing.get('transport_cost', 0))))
        labour_cost = Decimal(str(body.get('labour_cost', existing.get('labour_cost', 0))))
        other_cost = Decimal(str(body.get('other_cost', existing.get('other_cost', 0))))
        
        # Recalculate costs
        stock_items = dynamodb_service.scan_table('STOCK')
        stock_map = {item['item_id']: item for item in stock_items}
        
        base_cost = Decimal('0')
        max_produce = None
        cost_breakdown = {}
        
        for item_id, qty_needed in stock_needed.items():
            qty_needed_dec = Decimal(str(qty_needed))
            if item_id not in stock_map:
                max_produce = Decimal('0')
                base_cost = Decimal('0')
                cost_breakdown = {}
                break
                
            stock_item = stock_map[item_id]
            available = Decimal(str(stock_item.get('quantity', 0)))
            possible = available // qty_needed_dec if qty_needed_dec > 0 else Decimal('0')
            max_produce = possible if max_produce is None else min(max_produce, possible)
            
            cpu = Decimal(str(stock_item.get('cost_per_unit', 0)))
            cost_item = cpu * qty_needed_dec
            cost_breakdown[item_id] = cost_item
            base_cost += cost_item
            
        if max_produce is None:
            max_produce = Decimal('0')
            
        # Calculate totals
        wastage_amount = (base_cost * wastage_percent) / Decimal('100')
        total_cost = base_cost + wastage_amount + transport_cost + labour_cost + other_cost
        
        # Update product
        existing.update({
            'stock_needed': stock_needed,
            'wastage_percent': wastage_percent,
            'transport_cost': transport_cost,
            'labour_cost': labour_cost,
            'other_cost': other_cost,
            'max_produce': max_produce,
            'production_cost_breakdown': cost_breakdown,
            'production_cost_total': base_cost,
            'wastage_amount': wastage_amount,
            'total_cost': total_cost,
            'inventory': max_produce,
            'updated_at': datetime.now().isoformat()
        })
        
        dynamodb_service.put_item('PRODUCTION', existing)
        log_transaction("UpdateProduct", {
            'product_id': product_id,
            'production_cost_total': float(total_cost),
            'wastage_amount': float(wastage_amount),
            'total_cost': float(total_cost)
        }, username)
        
        return JsonResponse({
            'message': 'Product updated successfully',
            'product_id': product_id,
            'total_cost': float(total_cost),
            'max_produce': float(max_produce)
        })
        
    except Exception as e:
        logger.error(f"Error in update_product: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@jwt_required
@admin_required
def delete_product(request):
    try:
        from backend.dynamodb_service import dynamodb_service
        
        body = json.loads(request.body)
        
        required = ['product_id', 'username']
        missing = [f for f in required if f not in body]
        if missing:
            return JsonResponse({"error": f"Missing required field(s): {', '.join(missing)}"}, status=400)

        product_id = body['product_id']
        username = body['username']
        
        # Check if product exists
        products = dynamodb_service.scan_table('PRODUCTION')
        existing = None
        for product in products:
            if product.get('product_id') == product_id:
                existing = product
                break
                
        if not existing:
            return JsonResponse({"error": "Product not found"}, status=404)
            
        # Delete product
        dynamodb_service.delete_item('PRODUCTION', {'product_id': product_id})
        log_transaction("DeleteProduct", {
            "product_id": product_id,
            "product_name": existing.get('product_name', '')
        }, username)
        
        return JsonResponse({
            "message": "Product deleted successfully",
            "product_id": product_id
        })
        
    except Exception as e:
        logger.error(f"Error in delete_product: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_all_products(request):
    try:
        from backend.dynamodb_service import dynamodb_service
        products = dynamodb_service.scan_table('PRODUCTION')
        return JsonResponse(products, safe=False)
    except Exception as e:
        logger.error(f"Error in get_all_products: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@jwt_required
def push_to_production(request):
    try:
        from backend.dynamodb_service import dynamodb_service
        
        body = json.loads(request.body)
        
        required = ['product_id', 'quantity', 'username']
        missing = [f for f in required if f not in body]
        if missing:
            return JsonResponse({"error": f"Missing required field(s): {', '.join(missing)}"}, status=400)

        product_id = body['product_id']
        quantity_to_produce = Decimal(str(body['quantity']))
        username = body['username']
        
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
        cost_per_unit_total = Decimal('0')
        
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
@jwt_required
def undo_production(request):
    try:
        from backend.dynamodb_service import dynamodb_service
        
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
@jwt_required
@admin_required
def delete_push_to_production(request):
    try:
        from backend.dynamodb_service import dynamodb_service
        
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
@jwt_required
def get_daily_push_to_production(request):
    try:
        from backend.dynamodb_service import dynamodb_service
        from collections import defaultdict
        
        body = json.loads(request.body) if request.body else {}
        username = body.get('username', 'Unknown')
        date_str = body.get('date')
        
        if not date_str:
            return JsonResponse({"error": "'date' is required (format: YYYY-MM-DD)"}, status=400)
            
        # Get all push records
        push_records = dynamodb_service.scan_table('PUSH_TO_PRODUCTION')
        
        # Filter by date
        daily_items = [
            item for item in push_records
            if item.get('timestamp', '').startswith(date_str)
        ]
        
        # Group by product for summary
        product_summary = defaultdict(lambda: {"product_name": "", "total_quantity": 0})
        
        for item in daily_items:
            product_id = item.get('product_id', 'Unknown')
            product_name = item.get('product_name', 'Unknown')
            quantity = float(item.get('quantity_produced', 0))
            
            product_summary[product_id]["product_name"] = product_name
            product_summary[product_id]["total_quantity"] += quantity
            
        # Convert to list
        summary_list = [
            {
                "product_id": product_id,
                "product_name": data["product_name"],
                "total_quantity": data["total_quantity"]
            }
            for product_id, data in product_summary.items()
        ]
        
        return JsonResponse({
            "summary": summary_list,
            "items": daily_items
        }, cls=DecimalEncoder)
        
    except Exception as e:
        logger.error(f"Error in get_daily_push_to_production: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@jwt_required
def get_weekly_push_to_production(request):
    try:
        from backend.dynamodb_service import dynamodb_service
        from collections import defaultdict
        from datetime import datetime
        
        body = json.loads(request.body) if request.body else {}
        username = body.get('username', 'Unknown')
        from_str = body.get('from_date')
        to_str = body.get('to_date')
        
        if not from_str or not to_str:
            return JsonResponse({"error": "'from_date' and 'to_date' are required (format: YYYY-MM-DD)"}, status=400)
            
        from_date = datetime.strptime(from_str, "%Y-%m-%d").date()
        to_date = datetime.strptime(to_str, "%Y-%m-%d").date()
        
        # Get all push records
        push_records = dynamodb_service.scan_table('PUSH_TO_PRODUCTION')
        
        # Filter by date range
        weekly_items = []
        for item in push_records:
            timestamp = item.get('timestamp')
            if timestamp:
                dt = datetime.strptime(timestamp[:10], "%Y-%m-%d").date()
                if from_date <= dt <= to_date:
                    weekly_items.append(item)
                    
        # Group by product for summary
        product_summary = defaultdict(lambda: {"product_name": "", "total_quantity": 0})
        
        for item in weekly_items:
            product_id = item.get('product_id', 'Unknown')
            product_name = item.get('product_name', 'Unknown')
            quantity = float(item.get('quantity_produced', 0))
            
            product_summary[product_id]["product_name"] = product_name
            product_summary[product_id]["total_quantity"] += quantity
            
        # Convert to list
        summary_list = [
            {
                "product_id": product_id,
                "product_name": data["product_name"],
                "total_quantity": data["total_quantity"]
            }
            for product_id, data in product_summary.items()
        ]
        
        return JsonResponse({
            "summary": summary_list,
            "items": weekly_items
        }, cls=DecimalEncoder)
        
    except Exception as e:
        logger.error(f"Error in get_weekly_push_to_production: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
def get_monthly_push_to_production_public(request):
    try:
        from backend.dynamodb_service import dynamodb_service
        from collections import defaultdict
        from datetime import datetime
        
        body = json.loads(request.body) if request.body else {}
        from_str = body.get('from_date')
        to_str = body.get('to_date')
        
        if not from_str or not to_str:
            return JsonResponse({"error": "'from_date' and 'to_date' are required (format: YYYY-MM-DD)"}, status=400)
            
        from_date = datetime.strptime(from_str, "%Y-%m-%d").date()
        to_date = datetime.strptime(to_str, "%Y-%m-%d").date()
        
        # Get all push records
        push_records = dynamodb_service.scan_table('PUSH_TO_PRODUCTION')
        
        # Filter by date range
        monthly_items = []
        for item in push_records:
            timestamp = item.get('timestamp')
            if timestamp:
                dt = datetime.strptime(timestamp[:10], "%Y-%m-%d").date()
                if from_date <= dt <= to_date:
                    monthly_items.append(item)
                    
        # Group by product for summary
        product_summary = defaultdict(lambda: {"product_name": "", "total_quantity": 0})
        
        for item in monthly_items:
            product_id = item.get('product_id', 'Unknown')
            product_name = item.get('product_name', 'Unknown')
            quantity = float(item.get('quantity_produced', 0))
            
            product_summary[product_id]["product_name"] = product_name
            product_summary[product_id]["total_quantity"] += quantity
            
        # Convert to list
        summary_list = [
            {
                "product_id": product_id,
                "product_name": data["product_name"],
                "total_quantity": data["total_quantity"]
            }
            for product_id, data in product_summary.items()
        ]
        
        return JsonResponse({
            "summary": summary_list,
            "items": monthly_items
        }, cls=DecimalEncoder)
        
    except Exception as e:
        logger.error(f"Error in get_monthly_push_to_production_public: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)