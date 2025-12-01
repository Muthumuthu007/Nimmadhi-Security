import json
import uuid
import logging
from decimal import Decimal
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from backend.dynamodb_service import dynamodb_service
from backend.validators import InputValidator, validate_request_data
from backend.error_handlers import SecureErrorHandler
from backend.secure_db_service import SecureDatabaseService
from backend.security_monitor import SecurityMonitor
from users.decorators import jwt_required, admin_required
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

@csrf_protect
@require_http_methods(["POST"])
@jwt_required
@validate_request_data(required_fields=['product_name', 'stock_needed', 'username', 'labour_cost', 'transport_cost', 'other_cost', 'wastage_percent'])
def create_casting_product(request):
    try:
        body = request.validated_data
        
        # Validate and sanitize inputs
        product_name = InputValidator.sanitize_string(body['product_name'], 100)
        if not product_name:
            return SecureErrorHandler.validation_error("Invalid product name")
        
        username = InputValidator.sanitize_string(body['username'], 50)
        if not InputValidator.validate_username(username):
            return SecureErrorHandler.validation_error("Invalid username format")
        
        # Validate numeric inputs
        if not InputValidator.validate_decimal(body['labour_cost'], 0, 999999):
            return SecureErrorHandler.validation_error("Invalid labour cost")
        if not InputValidator.validate_decimal(body['transport_cost'], 0, 999999):
            return SecureErrorHandler.validation_error("Invalid transport cost")
        if not InputValidator.validate_decimal(body['other_cost'], 0, 999999):
            return SecureErrorHandler.validation_error("Invalid other cost")
        if not InputValidator.validate_decimal(body['wastage_percent'], 0, 100):
            return SecureErrorHandler.validation_error("Invalid wastage percentage")
        
        product_id = str(uuid.uuid4())
        stock_needed = body['stock_needed']
        labour_cost = Decimal(str(body['labour_cost']))
        transport_cost = Decimal(str(body['transport_cost']))
        other_cost = Decimal(str(body['other_cost']))
        wastage_percent = Decimal(str(body['wastage_percent']))
        
        # Check if product already exists for this user
        user_products = SecureDatabaseService.get_user_products(username, 'CASTING_PRODUCTS')
        for product in user_products:
            if product.get('product_name') == product_name:
                return JsonResponse({"error": "Product already exists in casting"}, status=400)

        # Calculate costs (basic calculation - can be enhanced)
        production_cost_total = labour_cost + transport_cost + other_cost
        total_cost = production_cost_total
        wastage_amount = total_cost * (wastage_percent / 100)
        
        # Calculate production cost breakdown from stock_needed
        production_cost_breakdown = {}
        for item_id, qty_str in stock_needed.items():
            # This would normally calculate based on stock costs, using placeholder for now
            production_cost_breakdown[item_id] = "0.00"
        
        casting_product = {
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
            'production_cost_breakdown': production_cost_breakdown,
            'inventory': 0,
            'max_produce': 0,
            'original_max_produce': 0,
            'created_at': datetime.now().isoformat()
        }
        
        # Record security event
        SecurityMonitor.record_security_event(
            'product_created', 
            user=username, 
            ip_address=request.META.get('REMOTE_ADDR'),
            details={'product_id': product_id}
        )
        
        logger.info(f"Creating casting product for user: {username}")
        result = dynamodb_service.put_item('CASTING_PRODUCTS', casting_product)
        logger.info(f"Casting product created successfully: {product_id}")
        
        return JsonResponse({
            "message": "Casting product created successfully",
            "product_id": product_id,
            "product_name": product_name
        })
        
    except Exception as e:
        return SecureErrorHandler.handle_error(e, "product creation")

@csrf_protect
@require_http_methods(["POST"])
@jwt_required
@validate_request_data(required_fields=['product_id'])
def move_to_production(request):
    try:
        body = request.validated_data
        product_id = body['product_id']
        
        # Validate product_id format
        if not InputValidator.validate_uuid(product_id):
            return SecureErrorHandler.validation_error("Invalid product ID format")
        
        # Verify user owns the product
        casting_product = SecureDatabaseService.check_product_ownership(
            product_id, 
            request.user_info.get('username'), 
            'CASTING_PRODUCTS'
        )
        if not casting_product:
            SecurityMonitor.record_suspicious_activity(
                request.META.get('REMOTE_ADDR'), 
                'unauthorized_product_access'
            )
            return JsonResponse({"error": "Casting product not found"}, status=404)
        
        # Transfer to production table
        production_product = {
            'product_id': casting_product['product_id'],
            'product_name': casting_product['product_name'],
            'stock_needed': casting_product['stock_needed'],
            'username': casting_product['username'],
            'created_at': casting_product['created_at'],
            'moved_to_production_at': datetime.now().isoformat()
        }
        
        # Add to production table
        dynamodb_service.put_item('PRODUCTION', production_product)
        
        # Remove from casting table
        dynamodb_service.delete_item('CASTING_PRODUCTS', {'product_id': product_id})
        
        logger.info(f"Product moved to production by user: {request.user_info.get('username')}")
        
        return JsonResponse({
            "message": "Casting product moved to production successfully",
            "product_id": product_id,
            "product_name": casting_product['product_name']
        })
        
    except Exception as e:
        return SecureErrorHandler.handle_error(e, "moving product to production")

@csrf_protect
@require_http_methods(["POST"])
@jwt_required
@validate_request_data(required_fields=['product_id'])
def delete_casting_product(request):
    try:
        body = request.validated_data
        product_id = body['product_id']
        
        # Validate product_id format
        if not InputValidator.validate_uuid(product_id):
            return SecureErrorHandler.validation_error("Invalid product ID format")
        
        # Verify user owns the product
        existing = SecureDatabaseService.check_product_ownership(
            product_id, 
            request.user_info.get('username'), 
            'CASTING_PRODUCTS'
        )
        if not existing:
            SecurityMonitor.record_suspicious_activity(
                request.META.get('REMOTE_ADDR'), 
                'unauthorized_delete_attempt'
            )
            return JsonResponse({"error": "Casting product not found"}, status=404)
        
        # Delete the product
        dynamodb_service.delete_item('CASTING_PRODUCTS', {'product_id': product_id})
        
        logger.info(f"Casting product deleted by user: {request.user_info.get('username')}")
        return JsonResponse({
            "message": "Casting product deleted successfully",
            "product_id": product_id
        })
        
    except Exception as e:
        return SecureErrorHandler.handle_error(e, "product deletion")

@csrf_protect
@require_http_methods(["GET"])
@jwt_required
def get_all_casting_products(request):
    try:
        username = request.user_info.get('username')
        user_role = request.user_info.get('role', 'user')
        
        # Get user-specific products or all products for admin
        if user_role == 'admin':
            casting_products = dynamodb_service.scan_table('CASTING_PRODUCTS')
        else:
            casting_products = SecureDatabaseService.get_user_products(username, 'CASTING_PRODUCTS')
        
        # Sanitize results based on user role
        sanitized_products = SecureDatabaseService.sanitize_scan_results(casting_products, user_role)
        
        logger.info(f"User {username} retrieved {len(sanitized_products)} casting products")
        return JsonResponse(sanitized_products, safe=False)
        
    except Exception as e:
        return SecureErrorHandler.handle_error(e, "retrieving products")