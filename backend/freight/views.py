"""
Freight Inward Note Views
"""
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import FreightInwardService
from decimal import Decimal, InvalidOperation
from datetime import datetime


def decimal_serializer(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


@csrf_exempt
@require_http_methods(["POST"])
def create_freight_note(request):
    """Create a new freight inward note"""
    try:
        if hasattr(request, '_body'):
            body = json.loads(request._body.decode('utf-8'))
        else:
            body = json.loads(request.body)
        
        # Extract required fields
        transport_vendor = body.get('transport_vendor')
        total_amount = body.get('total_amount')
        date = body.get('date')
        created_by = body.get('created_by', 'system')
        allocations = body.get('allocations', [])
        
        # Validate required fields
        if not transport_vendor:
            return JsonResponse({'error': 'Transport vendor is required'}, status=400)
        
        if not total_amount:
            return JsonResponse({'error': 'Total amount is required'}, status=400)
        
        if not date:
            return JsonResponse({'error': 'Date is required'}, status=400)
        
        if not allocations:
            return JsonResponse({'error': 'At least one allocation is required'}, status=400)
        
        # Validate allocations
        for allocation in allocations:
            if not allocation.get('supplier_name'):
                return JsonResponse({'error': 'Supplier name is required for all allocations'}, status=400)
            if not allocation.get('amount'):
                return JsonResponse({'error': 'Amount is required for all allocations'}, status=400)
        
        # Create freight note
        service = FreightInwardService()
        freight_note = service.create_freight_note(
            transport_vendor=transport_vendor,
            total_amount=total_amount,
            date=date,
            created_by=created_by,
            allocations=allocations
        )
        
        return JsonResponse({
            'message': 'Freight note created successfully',
            'freight_note': json.loads(json.dumps(freight_note, default=decimal_serializer))
        })
        
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Failed to create freight note: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def get_freight_note(request):
    """Get a specific freight note"""
    try:
        if hasattr(request, '_body'):
            body = json.loads(request._body.decode('utf-8'))
        else:
            body = json.loads(request.body)
        
        freight_id = body.get('freight_id')
        if not freight_id:
            return JsonResponse({'error': 'Freight ID is required'}, status=400)
        
        service = FreightInwardService()
        freight_note = service.get_freight_note(freight_id)
        
        if not freight_note:
            return JsonResponse({'error': 'Freight note not found'}, status=404)
        
        return JsonResponse({
            'freight_note': json.loads(json.dumps(freight_note, default=decimal_serializer))
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Failed to get freight note: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def list_freight_notes(request):
    """List all freight notes"""
    try:
        service = FreightInwardService()
        freight_notes = service.list_freight_notes()
        
        return JsonResponse({
            'freight_notes': json.loads(json.dumps(freight_notes, default=decimal_serializer))
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Failed to list freight notes: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_freight_note(request):
    """Update a freight note"""
    try:
        if hasattr(request, '_body'):
            body = json.loads(request._body.decode('utf-8'))
        else:
            body = json.loads(request.body)
        
        freight_id = body.get('freight_id')
        if not freight_id:
            return JsonResponse({'error': 'Freight ID is required'}, status=400)
        
        transport_vendor = body.get('transport_vendor')
        total_amount = body.get('total_amount')
        date = body.get('date')
        allocations = body.get('allocations')
        
        service = FreightInwardService()
        freight_note = service.update_freight_note(
            freight_id=freight_id,
            transport_vendor=transport_vendor,
            total_amount=total_amount,
            date=date,
            allocations=allocations
        )
        
        return JsonResponse({
            'message': 'Freight note updated successfully',
            'freight_note': json.loads(json.dumps(freight_note, default=decimal_serializer))
        })
        
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Failed to update freight note: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def delete_freight_note(request):
    """Delete a freight note"""
    try:
        if hasattr(request, '_body'):
            body = json.loads(request._body.decode('utf-8'))
        else:
            body = json.loads(request.body)
        
        freight_id = body.get('freight_id')
        if not freight_id:
            return JsonResponse({'error': 'Freight ID is required'}, status=400)
        
        service = FreightInwardService()
        service.delete_freight_note(freight_id)
        
        return JsonResponse({'message': 'Freight note deleted successfully'})
        
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Failed to delete freight note: {str(e)}'}, status=500)