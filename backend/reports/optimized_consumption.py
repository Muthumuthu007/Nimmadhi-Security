"""
Optimized consumption reports with batch operations and caching
"""
import json
import calendar
import logging
from decimal import Decimal
from datetime import datetime, timedelta, date
from collections import defaultdict
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from backend.dynamodb_service import dynamodb_service
from boto3.dynamodb.conditions import Attr, Key
from users.decorators import jwt_required

logger = logging.getLogger(__name__)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

def batch_get_group_chains(group_ids):
    """Batch fetch all groups and build chains efficiently"""
    if not group_ids:
        return {}
    
    # Cache key for groups
    cache_key = "all_groups_map"
    groups_map = cache.get(cache_key)
    
    if not groups_map:
        groups = dynamodb_service.scan_table('GROUPS')
        groups_map = {g['group_id']: g for g in groups}
        cache.set(cache_key, groups_map, 600)  # Cache for 10 minutes
    
    # Build chains for all group_ids
    chains = {}
    for group_id in group_ids:
        chain = []
        current_id = group_id
        while current_id and current_id in groups_map:
            grp = groups_map[current_id]
            chain.insert(0, grp['name'])
            current_id = grp.get('parent_id')
        chains[group_id] = chain
    
    return chains

def extract_consumption_details(transactions):
    """Extract consumption from AddDefectiveGoods & PushToProduction operations"""
    details = []
    for tx in transactions:
        op = tx.get("operation_type")
        if op == "PushToProduction":
            d = tx.get("details", {})
            for item_id, qty in d.get("deductions", {}).items():
                details.append({
                    "item_id": item_id,
                    "quantity_consumed": Decimal(str(qty)),
                    "timestamp": tx.get("timestamp", "")
                })
        elif op == "AddDefectiveGoods":
            d = tx.get("details", {})
            details.append({
                "item_id": d.get("item_id", "Unknown"),
                "quantity_consumed": Decimal(str(d.get("defective_added", 0))),
                "timestamp": tx.get("timestamp", "")
            })
    return details

def extract_inward_details(transactions):
    """Extract inward stock additions from AddStockQuantity operations"""
    details = []
    for tx in transactions:
        if tx.get("operation_type") == "AddStockQuantity":
            d = tx.get("details", {})
            details.append({
                "item_id": d.get("item_id", "Unknown"),
                "quantity_added": Decimal(str(d.get("quantity_added", 0))),
                "added_cost": Decimal(str(d.get("added_cost", 0))),
                "supplier_name": d.get("supplier_name", "Unknown"),
                "timestamp": tx.get("timestamp", "")
            })
    return details

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def get_daily_consumption_summary(request, body=None):
    """Optimized daily consumption summary"""
    try:
        if body is None:
            body = json.loads(request.body)

        if body.get("operation") != "GetDailyConsumptionSummary":
            return JsonResponse({"error": "Invalid operation for daily consumption summary."}, status=400)

        # Determine report_date (IST)
        report_date = body.get("report_date")
        if not report_date:
            report_date = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")
        report_date = report_date.strip()

        # Check cache first
        cache_key = f"daily_consumption_{report_date}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return JsonResponse(cached_result, encoder=DecimalEncoder)

        # Query transactions using DateIndex
        try:
            txns = dynamodb_service.query_table(
                'stock_transactions',
                IndexName='DateIndex',
                KeyConditionExpression=Key('date').eq(report_date)
            )
        except:
            txns = dynamodb_service.scan_table(
                'stock_transactions',
                FilterExpression=Attr('date').eq(report_date)
            )

        consumption_details = extract_consumption_details(txns)
        inward_details = extract_inward_details(txns)

        # Summarize consumption per-item
        consumption_map = defaultdict(Decimal)
        for d in consumption_details:
            consumption_map[d['item_id']] += d['quantity_consumed']

        # Summarize inward per-item
        inward_map = defaultdict(lambda: {'quantity': Decimal('0'), 'cost': Decimal('0'), 'suppliers': set()})
        for d in inward_details:
            item_id = d['item_id']
            inward_map[item_id]['quantity'] += d['quantity_added']
            inward_map[item_id]['cost'] += d['added_cost']
            inward_map[item_id]['suppliers'].add(d['supplier_name'])

        # Batch get all stock items at once
        all_items = list(set(consumption_map.keys()) | set(inward_map.keys()))
        stock_items = dynamodb_service.batch_get_items('STOCK', [{'item_id': item_id} for item_id in all_items])
        stock_lookup = {item['item_id']: item for item in stock_items}

        # Batch get all group chains
        group_ids = [stock_lookup[item_id].get('group_id') for item_id in all_items if item_id in stock_lookup]
        group_chains = batch_get_group_chains([gid for gid in group_ids if gid])

        # Build flat list
        flat = []
        for item_id in all_items:
            stock_item = stock_lookup.get(item_id, {})
            group_id = stock_item.get('group_id')
            chain = group_chains.get(group_id, []) if group_id else []
            
            consumed_qty = float(consumption_map.get(item_id, Decimal('0')))
            inward_data = inward_map.get(item_id, {'quantity': Decimal('0'), 'cost': Decimal('0'), 'suppliers': set()})
            
            flat.append({
                "item_id": item_id,
                "group": chain[0] if len(chain) >= 1 else None,
                "subgroup": chain[1] if len(chain) >= 2 else None,
                "total_quantity_consumed": consumed_qty,
                "total_quantity_added": float(inward_data['quantity']),
                "total_added_cost": float(inward_data['cost']),
                "suppliers": list(inward_data['suppliers']) if inward_data['suppliers'] else [],
                "cost_per_unit": float(stock_item.get('cost_per_unit', 0))
            })

        # Nest into groups
        nested = {}
        for e in flat:
            g = e['group'] or "Unknown"
            s = e['subgroup'] or "Unknown"
            nested.setdefault(g, {}).setdefault(s, []).append({
                "item_id": e["item_id"],
                "total_quantity_consumed": e["total_quantity_consumed"],
                "total_quantity_added": e["total_quantity_added"],
                "total_added_cost": e["total_added_cost"],
                "suppliers": e["suppliers"]
            })

        # Compute totals
        total_consumed_qty = sum(consumption_map.values())
        total_consumed_amt = sum(Decimal(str(e['cost_per_unit'])) * Decimal(str(e['total_quantity_consumed'])) for e in flat)
        total_added_qty = sum(data['quantity'] for data in inward_map.values())
        total_added_amt = sum(data['cost'] for data in inward_map.values())

        payload = {
            "report_date": report_date,
            "stock_summary": nested,
            "total_consumption_quantity": float(total_consumed_qty),
            "total_consumption_amount": float(total_consumed_amt),
            "total_inward_quantity": float(total_added_qty),
            "total_inward_amount": float(total_added_amt)
        }

        # Cache for 5 minutes
        cache.set(cache_key, payload, 300)
        return JsonResponse(payload, encoder=DecimalEncoder)

    except Exception as e:
        logger.error(f"Error in get_daily_consumption_summary: {e}", exc_info=True)
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def get_weekly_consumption_summary(request, body=None):
    """Optimized weekly consumption summary"""
    try:
        if body is None:
            body = json.loads(request.body)

        now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        end_date = body.get("end_date", now.strftime("%Y-%m-%d")).strip()
        start_date = body.get("start_date", (now - timedelta(days=7)).strftime("%Y-%m-%d")).strip()

        # Check cache
        cache_key = f"weekly_consumption_{start_date}_{end_date}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return JsonResponse(cached_result, encoder=DecimalEncoder)

        sd_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        ed_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Scan transactions in date range
        date_filter = Attr('date').gte(start_date) & Attr('date').lte(end_date)
        txns = dynamodb_service.scan_table('stock_transactions', FilterExpression=date_filter)

        consumption_details = extract_consumption_details(txns)

        # Get unique item_ids
        item_ids = list(set(d['item_id'] for d in consumption_details))
        
        # Batch get stock items
        stock_items = dynamodb_service.batch_get_items('STOCK', [{'item_id': item_id} for item_id in item_ids])
        stock_lookup = {item['item_id']: item for item in stock_items}

        # Batch get group chains
        group_ids = [stock_lookup[item_id].get('group_id') for item_id in item_ids if item_id in stock_lookup]
        group_chains = batch_get_group_chains([gid for gid in group_ids if gid])

        # Build flat list
        flat = []
        for d in consumption_details:
            item_id = d['item_id']
            qty = d['quantity_consumed']
            date_key = d['timestamp'].split(' ')[0]
            
            stock_item = stock_lookup.get(item_id, {})
            group_id = stock_item.get('group_id')
            chain = group_chains.get(group_id, []) if group_id else []
            
            flat.append({
                "date": date_key,
                "group": chain[0] if len(chain) >= 1 else "Unknown",
                "subgroup": chain[1] if len(chain) >= 2 else "Unknown",
                "item_id": item_id,
                "quantity": float(qty),
                "cost_per_unit": float(stock_item.get('cost_per_unit', 0))
            })

        # Initialize nested structure
        nested = {}
        cur = sd_dt
        while cur <= ed_dt:
            nested[cur.strftime("%Y-%m-%d")] = {}
            cur += timedelta(days=1)

        # Populate nested structure
        for e in flat:
            dt = e['date']
            g = e['group']
            s = e['subgroup']
            nested.setdefault(dt, {}).setdefault(g, {}).setdefault(s, []).append({
                "item_id": e["item_id"],
                "quantity": e["quantity"]
            })

        # Compute totals
        total_qty = sum(Decimal(str(e['quantity'])) for e in flat)
        total_amt = sum(Decimal(str(e['cost_per_unit'])) * Decimal(str(e['quantity'])) for e in flat)

        payload = {
            "report_date": end_date,
            "consumption_summary": nested,
            "total_consumption_quantity": float(total_qty),
            "total_consumption_amount": float(total_amt)
        }

        # Cache for 5 minutes
        cache.set(cache_key, payload, 300)
        return JsonResponse(payload, encoder=DecimalEncoder)

    except Exception as e:
        logger.error(f"Error in get_weekly_consumption_summary: {e}", exc_info=True)
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def get_monthly_consumption_summary(request, body=None):
    """Optimized monthly consumption summary"""
    try:
        if body is None:
            body = json.loads(request.body)

        month_str = body.get("month")
        if not isinstance(month_str, str):
            return JsonResponse({"error": "'month' parameter is required in format YYYY-MM"}, status=400)
        month_str = month_str.strip()
        
        try:
            year, month = map(int, month_str.split("-"))
        except ValueError:
            return JsonResponse({"error": "'month' must be in format YYYY-MM"}, status=400)

        # Check cache
        cache_key = f"monthly_consumption_{month_str}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return JsonResponse(cached_result, encoder=DecimalEncoder)

        # Determine date range
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        start_date = first_day.strftime("%Y-%m-%d")
        end_date = last_day.strftime("%Y-%m-%d")

        # Scan transactions in date range
        date_filter = Attr('date').gte(start_date) & Attr('date').lte(end_date)
        txns = dynamodb_service.scan_table('stock_transactions', FilterExpression=date_filter)

        consumption_details = extract_consumption_details(txns)

        # Get unique item_ids
        item_ids = list(set(d['item_id'] for d in consumption_details))
        
        # Batch get stock items
        stock_items = dynamodb_service.batch_get_items('STOCK', [{'item_id': item_id} for item_id in item_ids])
        stock_lookup = {item['item_id']: item for item in stock_items}

        # Batch get group chains
        group_ids = [stock_lookup[item_id].get('group_id') for item_id in item_ids if item_id in stock_lookup]
        group_chains = batch_get_group_chains([gid for gid in group_ids if gid])

        # Build flat list
        flat = []
        for d in consumption_details:
            item_id = d['item_id']
            qty = d['quantity_consumed']
            date_key = d['timestamp'].split(' ')[0]
            
            stock_item = stock_lookup.get(item_id, {})
            group_id = stock_item.get('group_id')
            chain = group_chains.get(group_id, []) if group_id else []
            
            flat.append({
                "date": date_key,
                "group": chain[0] if len(chain) >= 1 else "Unknown",
                "subgroup": chain[1] if len(chain) >= 2 else "Unknown",
                "item_id": item_id,
                "quantity": float(qty),
                "cost_per_unit": float(stock_item.get('cost_per_unit', 0))
            })

        # Initialize nested structure
        nested = {}
        cur = first_day
        while cur <= last_day:
            nested[cur.strftime("%Y-%m-%d")] = {}
            cur += timedelta(days=1)

        # Populate nested structure
        for e in flat:
            dt = e['date']
            g = e['group']
            s = e['subgroup']
            nested.setdefault(dt, {}).setdefault(g, {}).setdefault(s, []).append({
                "item_id": e["item_id"],
                "quantity": e["quantity"]
            })

        # Compute totals
        total_qty = sum(Decimal(str(e['quantity'])) for e in flat)
        total_amt = sum(Decimal(str(e['cost_per_unit'])) * Decimal(str(e['quantity'])) for e in flat)

        payload = {
            "month": month_str,
            "start_date": start_date,
            "end_date": end_date,
            "consumption_summary": nested,
            "total_consumption_quantity": float(total_qty),
            "total_consumption_amount": float(total_amt)
        }

        # Cache for 10 minutes
        cache.set(cache_key, payload, 600)
        return JsonResponse(payload, encoder=DecimalEncoder)

    except Exception as e:
        logger.error(f"Error in get_monthly_consumption_summary: {e}", exc_info=True)
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)
