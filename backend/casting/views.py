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

@csrf_exempt
@require_http_methods(["POST"])
def create_casting_product(request):
    try:
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
        existing_products = dynamodb_service.scan_table('CASTING_PRODUCTS')
        for product in existing_products:
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
        
        logger.info(f"Attempting to save casting product: {casting_product}")
        result = dynamodb_service.put_item('CASTING_PRODUCTS', casting_product)
        logger.info(f"DynamoDB put_item result: {result}")
        logger.info(f"Casting product created: {product_id}")
        
        return JsonResponse({
            "message": "Casting product created successfully",
            "product_id": product_id,
            "product_name": product_name
        })
        
    except Exception as e:
        logger.error(f"Error in create_casting_product: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def move_to_production(request):
    try:
        body = json.loads(request.body)
        
        if 'product_id' not in body:
            return JsonResponse({"error": "'product_id' is required"}, status=400)

        product_id = body['product_id']
        
        # Get product from casting table
        casting_product = dynamodb_service.get_item('CASTING_PRODUCTS', {'product_id': product_id})
        if not casting_product:
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
        
        logger.info(f"Product moved to production: {product_id}")
        
        return JsonResponse({
            "message": "Casting product moved to production successfully",
            "product_id": product_id,
            "product_name": casting_product['product_name']
        })
        
    except Exception as e:
        logger.error(f"Error in move_to_production: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def delete_casting_product(request):
    try:
        body = json.loads(request.body)
        
        if 'product_id' not in body:
            return JsonResponse({"error": "'product_id' is required"}, status=400)

        product_id = body['product_id']
        
        # Check if product exists
        existing = dynamodb_service.get_item('CASTING_PRODUCTS', {'product_id': product_id})
        if not existing:
            return JsonResponse({"error": "Casting product not found"}, status=404)
        
        # Delete the product
        dynamodb_service.delete_item('CASTING_PRODUCTS', {'product_id': product_id})
        
        logger.info(f"Casting product deleted: {product_id}")
        return JsonResponse({
            "message": "Casting product deleted successfully",
            "product_id": product_id
        })
        
    except Exception as e:
        logger.error(f"Error in delete_casting_product: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_all_casting_products(request):
    try:
        casting_products = dynamodb_service.scan_table('CASTING_PRODUCTS')
        logger.info(f"Found {len(casting_products)} casting products")
        return JsonResponse(casting_products, safe=False)
        
    except Exception as e:
        logger.error(f"Error in get_all_casting_products: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)