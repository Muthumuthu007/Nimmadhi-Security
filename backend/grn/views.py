import json
import uuid
import logging
from decimal import Decimal
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from backend.dynamodb_service import dynamodb_service

logger = logging.getLogger(__name__)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

@csrf_exempt
@require_http_methods(["POST"])
def create_grn(request):
    """Create a new GRN record"""
    try:
        body = json.loads(request.body)
        
        # Required fields validation
        required_fields = [
            'date', 'supplierName', 'rawMaterial', 'billNumber',
            'billDate', 'billedQuantity', 'receivedQuantity', 'transport',
            'tallyReference', 'costing', 'taxPercentage', 'sgstAmount',
            'cgstAmount', 'totalAmount'
        ]
        
        for field in required_fields:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)
        
        # Generate UUID for grnId
        grn_id = str(uuid.uuid4())
        
        # Create GRN record
        grn_item = {
            'grnId': grn_id,
            'date': body['date'],
            'supplierName': body['supplierName'],
            'rawMaterial': body['rawMaterial'],
            'billNumber': body['billNumber'],
            'billDate': body['billDate'],
            'billedQuantity': Decimal(str(body['billedQuantity'])),
            'receivedQuantity': Decimal(str(body['receivedQuantity'])),
            'transport': body['transport'],
            'tallyReference': body['tallyReference'],
            'costing': Decimal(str(body['costing'])),
            'taxPercentage': Decimal(str(body['taxPercentage'])),
            'sgstAmount': Decimal(str(body['sgstAmount'])),
            'cgstAmount': Decimal(str(body['cgstAmount'])),
            'totalAmount': Decimal(str(body['totalAmount'])),
            'created_at': datetime.now().isoformat()
        }
        
        # Save to DynamoDB
        dynamodb_service.put_item('GRN_TABLE', grn_item)
        
        logger.info(f"GRN created successfully: {grn_id}")
        
        return JsonResponse({
            "message": "GRN created successfully",
            "grnId": grn_id,
            "date": body['date'],
            "supplierName": body['supplierName'],
            "rawMaterial": body['rawMaterial'],
            "billNumber": body['billNumber'],
            "billDate": body['billDate'],
            "billedQuantity": float(body['billedQuantity']),
            "receivedQuantity": float(body['receivedQuantity']),
            "transport": body['transport'],
            "tallyReference": body['tallyReference'],
            "costing": float(body['costing']),
            "taxPercentage": float(body['taxPercentage']),
            "sgstAmount": float(body['sgstAmount']),
            "cgstAmount": float(body['cgstAmount']),
            "totalAmount": float(body['totalAmount'])
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        logger.error(f"Error creating GRN: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_grn(request, grn_id):
    """Get GRN by ID"""
    try:
        # Get GRN from DynamoDB
        grn_item = dynamodb_service.get_item('GRN_TABLE', {'grnId': grn_id})
        
        if not grn_item:
            return JsonResponse({"error": "GRN not found"}, status=404)
        
        # Convert Decimal values to float for JSON response
        response_data = {}
        for key, value in grn_item.items():
            if isinstance(value, Decimal):
                response_data[key] = float(value)
            else:
                response_data[key] = value
        
        logger.info(f"GRN retrieved: {grn_id}")
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error retrieving GRN {grn_id}: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_grn(request, grn_id):
    """Delete GRN by ID"""
    try:
        # Check if GRN exists
        existing_grn = dynamodb_service.get_item('GRN_TABLE', {'grnId': grn_id})
        
        if not existing_grn:
            return JsonResponse({"error": "GRN not found"}, status=404)
        
        # Delete from DynamoDB
        dynamodb_service.delete_item('GRN_TABLE', {'grnId': grn_id})
        
        logger.info(f"GRN deleted: {grn_id}")
        return JsonResponse({"message": "GRN deleted successfully", "grnId": grn_id})
        
    except Exception as e:
        logger.error(f"Error deleting GRN {grn_id}: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_grn_by_transport(request, transport_type):
    """Get all GRN records filtered by transport type"""
    try:
        # Query using GSI for efficient transport-based filtering
        grn_records = dynamodb_service.query_table(
            'GRN_TABLE',
            IndexName='transport-index',
            KeyConditionExpression='transport = :transport_type',
            ExpressionAttributeValues={
                ':transport_type': transport_type
            }
        )
        
        if not grn_records:
            return JsonResponse({"message": "No data found", "data": []})
        
        # Convert Decimal values to float for JSON response
        response_data = []
        for record in grn_records:
            converted_record = {}
            for key, value in record.items():
                if isinstance(value, Decimal):
                    converted_record[key] = float(value)
                else:
                    converted_record[key] = value
            response_data.append(converted_record)
        
        logger.info(f"Found {len(response_data)} GRN records for transport: {transport_type}")
        return JsonResponse({
            "message": f"Found {len(response_data)} GRN records",
            "transport_type": transport_type,
            "data": response_data
        })
        
    except Exception as e:
        logger.error(f"Error retrieving GRN records for transport {transport_type}: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)