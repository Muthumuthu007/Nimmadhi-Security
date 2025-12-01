import json
import calendar
import logging
import boto3
from boto3.dynamodb.conditions import Attr, Key
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from datetime import datetime, timedelta, date
from collections import defaultdict
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.conf import settings
from backend.dynamodb_service import dynamodb_service
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)

def ensure_transactions_index():
    """
    Creates a Global Secondary Index (GSI) on stock_transactions
    to allow fast querying by 'operation_type' and 'date'.
    """
    try:
        client = boto3.client('dynamodb', region_name='us-east-2')
        table_desc = client.describe_table(TableName='stock_transactions')
        
        # Check if index already exists
        gsi_list = table_desc['Table'].get('GlobalSecondaryIndexes', [])
        if any(gsi['IndexName'] == 'OpTypeDateIndex' for gsi in gsi_list):
            logger.info("Index 'OpTypeDateIndex' already exists.")
            return

        logger.info("Creating index 'OpTypeDateIndex' on table 'stock_transactions'...")
        client.update_table(
            TableName='stock_transactions',
            AttributeDefinitions=[
                {'AttributeName': 'operation_type', 'AttributeType': 'S'},
                {'AttributeName': 'date', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexUpdates=[
                {
                    'Create': {
                        'IndexName': 'OpTypeDateIndex',
                        'KeySchema': [
                            {'AttributeName': 'operation_type', 'KeyType': 'HASH'},
                            {'AttributeName': 'date', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    }
                }
            ]
        )
        logger.info("Index creation initiated for 'OpTypeDateIndex'. It may take a few minutes to become Active.")
        
    except Exception as e:
        logger.error(f"Error ensuring index: {str(e)}")

def extract_consumption_details(transactions):
    """Extract consumption from AddDefectiveGoods & PushToProduction operations - exact Lambda match"""
    ops = ["AddDefectiveGoods", "PushToProduction"]
    details = []
    for tx in transactions:
        op = tx.get("operation_type")
        if op in ops:
            d = tx.get("details", {})
            if op == "PushToProduction":
                for item_id, qty in d.get("deductions", {}).items():
                    details.append({
                        "item_id": item_id,
                        "quantity_consumed": Decimal(str(qty)),
                        "timestamp": tx.get("timestamp", "")
                    })
            else:  # AddDefectiveGoods
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
        op = tx.get("operation_type")
        if op == "AddStockQuantity":
            d = tx.get("details", {})
            details.append({
                "item_id": d.get("item_id", "Unknown"),
                "quantity_added": Decimal(str(d.get("quantity_added", 0))),
                "added_cost": Decimal(str(d.get("added_cost", 0))),
                "supplier_name": d.get("supplier_name", "Unknown"),
                "timestamp": tx.get("timestamp", "")
            })
    return details

def get_group_chain(group_id):
    """Walk up Groups table to build [parent, ..., child] chain of names - exact Lambda match"""
    chain = []
    while group_id:
        grp = dynamodb_service.get_item('GROUPS', {'group_id': group_id})
        if not grp:
            break
        chain.insert(0, grp['name'])
        group_id = grp.get('parent_id')
    return chain

class DecimalEncoder(json.JSONEncoder):
    """JSON encoder for Decimal types - exact Lambda match"""
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

@csrf_exempt
@require_http_methods(["POST"])
def get_daily_consumption_summary(request, body=None):
    """Get daily stock report including both inward additions and consumption"""
    try:
        if body is None:
            body = json.loads(request.body)

        # 1) Validate operation - exact Lambda check
        if body.get("operation") != "GetDailyConsumptionSummary":
            return JsonResponse({"error": "Invalid operation for daily consumption summary."}, status=400)

        # 2) Determine report_date (IST) - exact Lambda logic
        report_date = body.get("report_date")
        if not report_date:
            report_date = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")
        report_date = report_date.strip()

        # 3) Load transactions efficiently with date index
        try:
            # Try GSI query first (faster)
            txns = dynamodb_service.query_table(
                'stock_transactions',
                IndexName='DateIndex',
                KeyConditionExpression=Key('date').eq(report_date)
            )
        except:
            # Fallback to scan with filter
            txns = dynamodb_service.scan_table(
                'stock_transactions',
                FilterExpression=Attr('date').eq(report_date)
            )

        # 4) Direct GSI query with date index only
        cache_key = f"daily_report_{report_date}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return JsonResponse(cached_result, encoder=DecimalEncoder)
        
        # Single fast query using DateIndex
        txns = dynamodb_service.query_table(
            'stock_transactions',
            IndexName='DateIndex',
            KeyConditionExpression=Key('date').eq(report_date)
        )
        
        consumption_details = extract_consumption_details(txns)
        inward_details = extract_inward_details(txns)

        # 6) Summarize consumption per‐item quantities - exact Lambda logic
        consumption_map = defaultdict(Decimal)
        for d in consumption_details:
            consumption_map[d['item_id']] += Decimal(str(d['quantity_consumed']))
            
        # 7) Summarize inward per-item quantities - NEW: track stock additions
        inward_map = defaultdict(lambda: {'quantity': Decimal('0'), 'cost': Decimal('0'), 'suppliers': set()})
        for d in inward_details:
            item_id = d['item_id']
            inward_map[item_id]['quantity'] += Decimal(str(d['quantity_added']))
            inward_map[item_id]['cost'] += Decimal(str(d['added_cost']))
            inward_map[item_id]['suppliers'].add(d['supplier_name'])

        # 8) Ultra-fast batch lookup for all items
        all_items = list(set(consumption_map.keys()) | set(inward_map.keys()))
        
        # Batch get all stock items at once (100x faster)
        stock_items = dynamodb_service.batch_get_items('STOCK', [{'item_id': item_id} for item_id in all_items])
        stock_lookup = {item['item_id']: item for item in stock_items}
        
        flat = []
        for item_id in all_items:
            stock_item = stock_lookup.get(item_id, {})
            group_id = stock_item.get('group_id')

            # build full chain: [top_group, sub_group, ...] - exact Lambda chain building
            chain = get_group_chain(group_id) if group_id else []
            group    = chain[0] if len(chain) >= 1 else None
            subgroup = chain[1] if len(chain) >= 2 else None
            
            # Get consumption and inward data
            consumed_qty = float(consumption_map.get(item_id, Decimal('0')))
            inward_data = inward_map.get(item_id, {'quantity': Decimal('0'), 'cost': Decimal('0'), 'suppliers': set()})
            added_qty = float(inward_data['quantity'])
            added_cost = float(inward_data['cost'])
            suppliers = list(inward_data['suppliers']) if inward_data['suppliers'] else []

            flat.append({
                "item_id":                 item_id,
                "group":                   group,
                "subgroup":                subgroup,
                "total_quantity_consumed": consumed_qty,
                "total_quantity_added":    added_qty,
                "total_added_cost":        added_cost,
                "suppliers":               suppliers
            })

        # 9) Nest into { group → { subgroup → [items…] } } - enhanced nesting
        nested = {}
        for e in flat:
            g = e['group'] or "Unknown"
            s = e['subgroup'] or "Unknown"
            nested.setdefault(g, {}).setdefault(s, []).append({
                "item_id":                 e["item_id"],
                "total_quantity_consumed": e["total_quantity_consumed"],
                "total_quantity_added":    e["total_quantity_added"],
                "total_added_cost":        e["total_added_cost"],
                "suppliers":               e["suppliers"]
            })

        # 10) Compute grand totals - enhanced calculation
        total_consumed_qty = sum(consumption_map.values())
        total_consumed_amt = Decimal('0')
        for item_id, qty in consumption_map.items():
            stock_item = dynamodb_service.get_item('STOCK', {'item_id': item_id})
            if stock_item:
                rate = Decimal(str(stock_item.get('cost_per_unit', 0)))
                total_consumed_amt += rate * qty
                
        total_added_qty = sum(data['quantity'] for data in inward_map.values())
        total_added_amt = sum(data['cost'] for data in inward_map.values())

        # 11) Build and return - enhanced payload with caching
        payload = {
            "report_date":                report_date,
            "stock_summary":              nested,
            "total_consumption_quantity": float(total_consumed_qty),
            "total_consumption_amount":   float(total_consumed_amt),
            "total_inward_quantity":      float(total_added_qty),
            "total_inward_amount":        float(total_added_amt)
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, payload, 300)
        return JsonResponse(payload, encoder=DecimalEncoder)

    except Exception as e:
        logger.error(f"Error in get_daily_consumption_summary: {e}", exc_info=True)
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_weekly_consumption_summary(request, body=None):
    """Get weekly consumption summary - exact Lambda replication"""
    try:
        if body is None:
            body = json.loads(request.body)
        
        # 1) Determine IST date window - exact Lambda logic
        now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        end_date = body.get("end_date", now.strftime("%Y-%m-%d")).strip()
        start_date = body.get("start_date", (now - timedelta(days=7)).strftime("%Y-%m-%d")).strip()
        
        # Parse into date objects
        sd_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        ed_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # 2) Scan all transactions in [start_date..end_date] - exact Lambda filter
        from boto3.dynamodb.conditions import Attr
        date_filter = Attr('date').gte(start_date) & Attr('date').lte(end_date)
        txns = dynamodb_service.scan_table('stock_transactions', FilterExpression=date_filter)
        
        # 3) Extract only consumption details - exact Lambda helper
        consumption_details = extract_consumption_details(txns)
        
        # 4) Prepare flat list enriched with date, group, subgroup - exact Lambda logic
        flat = []
        for d in consumption_details:
            item_id = d['item_id']
            qty = Decimal(str(d['quantity_consumed']))
            # Derive date from timestamp "YYYY-MM-DD hh:mm:ss AM/PM" - exact Lambda logic
            date_key = d['timestamp'].split(' ')[0]
            
            # Lookup group_id - exact Lambda lookup
            stock_item = dynamodb_service.get_item('STOCK', {'item_id': item_id})
            group_id = stock_item.get('group_id') if stock_item else None
            
            # Build group chain - exact Lambda chain building
            chain = get_group_chain(group_id) if group_id else []
            group = chain[0] if len(chain) >= 1 else "Unknown"
            subgroup = chain[1] if len(chain) >= 2 else "Unknown"
            
            flat.append({
                "date": date_key,
                "group": group,
                "subgroup": subgroup,
                "item_id": item_id,
                "quantity": float(qty)
            })
        
        # 5) Initialize nested structure with every date in range - exact Lambda logic
        nested = {}
        cur = sd_dt
        while cur <= ed_dt:
            nested[cur.strftime("%Y-%m-%d")] = {}
            cur += timedelta(days=1)
        
        # 6) Populate nested[date][group][subgroup] = [items...] - exact Lambda nesting
        for e in flat:
            dt = e['date']
            g = e['group']
            s = e['subgroup']
            nested.setdefault(dt, {}).setdefault(g, {}).setdefault(s, []).append({
                "item_id": e["item_id"],
                "quantity": e["quantity"]
            })
        
        # 7) Compute grand totals - exact Lambda calculation
        total_qty = sum(Decimal(str(e['quantity'])) for e in flat)
        total_amt = Decimal('0')
        for e in flat:
            stock_item = dynamodb_service.get_item('STOCK', {'item_id': e['item_id']})
            if stock_item:
                rate = Decimal(str(stock_item.get('cost_per_unit', 0)))
                total_amt += rate * Decimal(str(e['quantity']))
        
        # 8) Assemble and return - exact Lambda payload
        payload = {
            "report_date": end_date,
            "consumption_summary": nested,
            "total_consumption_quantity": float(total_qty),
            "total_consumption_amount": float(total_amt)
        }
        
        return JsonResponse(payload, encoder=DecimalEncoder)
        
    except Exception as e:
        logger.error(f"Error in get_weekly_consumption_summary: {e}", exc_info=True)
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_monthly_consumption_summary(request, body=None):
    """Get monthly consumption summary - exact Lambda replication"""
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
        
        # 1) Determine first and last day of month - exact Lambda logic
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        start_date = first_day.strftime("%Y-%m-%d")
        end_date = last_day.strftime("%Y-%m-%d")
        
        # Parse into date objects for iteration
        sd_dt = first_day
        ed_dt = last_day
        
        # 2) Scan all transactions in [start_date..end_date] - exact Lambda filter
        from boto3.dynamodb.conditions import Attr
        date_filter = Attr('date').gte(start_date) & Attr('date').lte(end_date)
        txns = dynamodb_service.scan_table('stock_transactions', FilterExpression=date_filter)
        
        # 3) Extract only consumption details - exact Lambda helper
        consumption_details = extract_consumption_details(txns)
        
        # 4) Prepare flat enriched list - exact Lambda logic
        flat = []
        for d in consumption_details:
            item_id = d['item_id']
            qty = Decimal(str(d['quantity_consumed']))
            date_key = d['timestamp'].split(' ')[0]
            
            stock_item = dynamodb_service.get_item('STOCK', {'item_id': item_id})
            group_id = stock_item.get('group_id') if stock_item else None
            
            chain = get_group_chain(group_id) if group_id else []
            group = chain[0] if len(chain) >= 1 else "Unknown"
            subgroup = chain[1] if len(chain) >= 2 else "Unknown"
            
            flat.append({
                "date": date_key,
                "group": group,
                "subgroup": subgroup,
                "item_id": item_id,
                "quantity": float(qty)
            })
        
        # 5) Initialize nested[date] - exact Lambda logic
        nested = {}
        cur = sd_dt
        while cur <= ed_dt:
            nested[cur.strftime("%Y-%m-%d")] = {}
            cur += timedelta(days=1)
        
        # 6) Populate nested[date][group][subgroup] - exact Lambda nesting
        for e in flat:
            dt = e['date']
            g = e['group']
            s = e['subgroup']
            nested.setdefault(dt, {}).setdefault(g, {}).setdefault(s, []).append({
                "item_id": e["item_id"],
                "quantity": e["quantity"]
            })
        
        # 7) Compute grand totals - exact Lambda calculation
        total_qty = sum(Decimal(str(e['quantity'])) for e in flat)
        total_amt = Decimal('0')
        for e in flat:
            stock_item = dynamodb_service.get_item('STOCK', {'item_id': e['item_id']})
            if stock_item:
                rate = Decimal(str(stock_item.get('cost_per_unit', 0)))
                total_amt += rate * Decimal(str(e['quantity']))
        
        # 8) Assemble and return - exact Lambda payload
        payload = {
            "month": month_str,
            "start_date": start_date,
            "end_date": end_date,
            "consumption_summary": nested,
            "total_consumption_quantity": float(total_qty),
            "total_consumption_amount": float(total_amt)
        }
        
        return JsonResponse(payload, encoder=DecimalEncoder)
        
    except Exception as e:
        logger.error(f"Error in get_monthly_consumption_summary: {e}", exc_info=True)
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_daily_inward(request):
    """Get daily inward report - direct URL access"""
    try:
        from .inward_service import InwardService
        
        body = json.loads(request.body) if request.body else {}
        report_date = body.get("report_date")
        
        payload = InwardService.get_daily_inward(report_date)
        return JsonResponse(payload, encoder=DecimalEncoder)
        
    except Exception as e:
        logger.error(f"Error in get_daily_inward: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_weekly_inward(request):
    """Get weekly inward report - direct URL access"""
    try:
        from .inward_service import InwardService
        
        body = json.loads(request.body) if request.body else {}
        start_date = body.get("start_date")
        end_date = body.get("end_date")
        
        payload = InwardService.get_weekly_inward(start_date, end_date)
        return JsonResponse(payload, encoder=DecimalEncoder)
        
    except Exception as e:
        logger.error(f"Error in get_weekly_inward: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_monthly_inward(request):
    """Get monthly inward report - direct URL access"""
    try:
        from .inward_service import InwardService
        import calendar
        
        body = json.loads(request.body) if request.body else {}
        month_str = body.get("month")
        
        if not month_str:
            now = datetime.utcnow() + timedelta(hours=5, minutes=30)
            month_str = now.strftime("%Y-%m")
        
        try:
            year, month = map(int, month_str.split("-"))
        except ValueError:
            return JsonResponse({"error": "'month' must be in YYYY-MM format"}, status=400)
        
        # Calculate month date range
        start_date = f"{year}-{month:02d}-01"
        last_day = calendar.monthrange(year, month)[1]
        end_date = f"{year}-{month:02d}-{last_day:02d}"
        
        # Use weekly inward logic for monthly range
        payload = InwardService.get_weekly_inward(start_date, end_date)
        payload["month"] = month_str
        
        return JsonResponse(payload, encoder=DecimalEncoder)
        
    except Exception as e:
        logger.error(f"Error in get_monthly_inward: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_all_stock_transactions(request):
    """Get all stock transactions - converted from Lambda get_all_stock_transactions function"""
    try:
        # Get all transactions from DynamoDB - using correct table name
        transactions = dynamodb_service.scan_table('stock_transactions')
        
        # Convert Decimal objects to float for JSON serialization
        processed_transactions = []
        for tx in transactions:
            processed_tx = {
                'transaction_id': tx.get('transaction_id', ''),
                'date': tx.get('date', ''),
                'timestamp': tx.get('timestamp', ''),
                'operation_type': tx.get('operation_type', ''),
                'details': {}
            }
            
            # Process details, converting Decimal to float
            details = tx.get('details', {})
            for key, value in details.items():
                if hasattr(value, '__float__'):  # Decimal objects
                    processed_tx['details'][key] = float(value)
                else:
                    processed_tx['details'][key] = value
            
            processed_transactions.append(processed_tx)
        
        # Sort by timestamp (newest first)
        processed_transactions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        logger.info(f"Retrieved {len(processed_transactions)} stock transaction records.")
        return JsonResponse(processed_transactions, safe=False)
        
    except Exception as e:
        logger.error(f"Error in get_all_stock_transactions: {str(e)}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_today_logs(request):
    """Get today's logs - converted from Lambda get_today_logs function"""
    try:
        body = json.loads(request.body)
        
        limit = body.get("limit")
        if limit is not None:
            try:
                limit = int(limit)
                if limit <= 0:
                    limit = None
            except (TypeError, ValueError):
                limit = None

        today = datetime.now().strftime("%Y-%m-%d")
        
        # Debug: Get all transactions to check date formats - using correct table name
        all_transactions = dynamodb_service.scan_table('stock_transactions')
        logger.info(f"Total transactions in DB: {len(all_transactions)}")
        if all_transactions:
            sample_dates = [tx.get('date') for tx in all_transactions[:5]]
            logger.info(f"Sample dates: {sample_dates}")
        
        # Get today's transactions from DynamoDB - using correct table name
        transactions = dynamodb_service.scan_table(
            'stock_transactions',
            FilterExpression='#date = :today',
            ExpressionAttributeNames={'#date': 'date'},
            ExpressionAttributeValues={':today': today}
        )
        
        logger.info(f"Looking for date: {today}, Found {len(transactions)} transactions")
        
        # Process and convert Decimal objects
        processed_logs = []
        for tx in transactions:
            processed_tx = {
                'transaction_id': tx.get('transaction_id', ''),
                'date': tx.get('date', ''),
                'timestamp': tx.get('timestamp', ''),
                'operation_type': tx.get('operation_type', ''),
                'details': {}
            }
            
            details = tx.get('details', {})
            for key, value in details.items():
                if hasattr(value, '__float__'):
                    processed_tx['details'][key] = float(value)
                else:
                    processed_tx['details'][key] = value
            
            processed_logs.append(processed_tx)
        
        # Sort by timestamp (newest first)
        processed_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Apply limit if specified
        if limit:
            processed_logs = processed_logs[:limit]
        
        payload = {
            "date": today,
            "count": len(processed_logs),
            "logs": processed_logs
        }
        
        return JsonResponse(payload)
        
    except Exception as e:
        logger.error(f"Error in get_today_logs: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_daily_push_to_production(request):
    """Get daily push to production report"""
    try:
        from backend.dynamodb_service import dynamodb_service
        from collections import defaultdict
        
        body = json.loads(request.body) if request.body else {}
        date_str = body.get('date')
        
        if not date_str:
            return JsonResponse({"error": "'date' is required (format: YYYY-MM-DD)"}, status=400)
            
        # Get all push records
        push_records = dynamodb_service.scan_table('push_to_production')
        
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
        })
        
    except Exception as e:
        logger.error(f"Error in get_daily_push_to_production: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_weekly_push_to_production(request):
    """Get weekly push to production report"""
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
        push_records = dynamodb_service.scan_table('push_to_production')
        
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
        })
        
    except Exception as e:
        logger.error(f"Error in get_weekly_push_to_production: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_monthly_push_to_production(request):
    """Get monthly push to production report"""
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
        push_records = dynamodb_service.scan_table('push_to_production')
        
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
        })
        
    except Exception as e:
        logger.error(f"Error in get_monthly_push_to_production: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_monthly_production_summary(request):
    """Get monthly production summary"""
    try:
        from backend.dynamodb_service import dynamodb_service
        from collections import defaultdict
        from datetime import datetime
        import calendar
        
        body = json.loads(request.body) if request.body else {}
        month_str = body.get('month')
        
        if not month_str:
            now = datetime.utcnow() + timedelta(hours=5, minutes=30)
            month_str = now.strftime("%Y-%m")
        
        try:
            year, month = map(int, month_str.split("-"))
        except ValueError:
            return JsonResponse({"error": "'month' must be in YYYY-MM format"}, status=400)
        
        # Calculate month date range
        start_date = f"{year}-{month:02d}-01"
        last_day = calendar.monthrange(year, month)[1]
        end_date = f"{year}-{month:02d}-{last_day:02d}"
        
        # Get all push records
        push_records = dynamodb_service.scan_table('push_to_production')
        
        # Filter by month
        monthly_items = []
        for item in push_records:
            timestamp = item.get('timestamp')
            if timestamp and start_date <= timestamp[:10] <= end_date:
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
            "month": month_str,
            "start_date": start_date,
            "end_date": end_date,
            "summary": summary_list,
            "items": monthly_items
        })
        
    except Exception as e:
        logger.error(f"Error in get_monthly_production_summary: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_item_history(request):
    """Get item history - converted from Lambda get_item_history function"""
    try:
        body = json.loads(request.body)
        
        item_id = body.get("item_id")
        if not isinstance(item_id, str) or not item_id.strip():
            return JsonResponse({"error": "'item_id' is required (string)"}, status=400)

        item_id = item_id.strip()
        order = (body.get("order") or "asc").lower()
        if order not in ("asc", "desc"):
            order = "asc"

        date_from = body.get("date_from")
        date_to = body.get("date_to")

        # Get all transactions - using correct table name
        filter_expr = None
        expr_attr_values = {}
        
        if date_from and date_to:
            filter_expr = '#date BETWEEN :date_from AND :date_to'
            expr_attr_values = {':date_from': date_from, ':date_to': date_to}
        elif date_from:
            filter_expr = '#date >= :date_from'
            expr_attr_values = {':date_from': date_from}
        elif date_to:
            filter_expr = '#date <= :date_to'
            expr_attr_values = {':date_to': date_to}
        
        if filter_expr:
            transactions = dynamodb_service.scan_table(
                'stock_transactions',
                FilterExpression=filter_expr,
                ExpressionAttributeNames={'#date': 'date'},
                ExpressionAttributeValues=expr_attr_values
            )
        else:
            transactions = dynamodb_service.scan_table('stock_transactions')
        
        # Filter transactions for this item
        item_events = []
        totals = {
            "added": 0.0,
            "subtracted": 0.0,
            "defective_added": 0.0,
            "defective_subtracted": 0.0,
            "consumed_by_production": 0.0
        }
        
        for tx in transactions:
            details = tx.get('details', {})
            tx_item_id = details.get('item_id')
            
            if tx_item_id == item_id:
                op_type = tx.get('operation_type', '')
                event = {
                    'transaction_id': tx.get('transaction_id', ''),
                    'date': tx.get('date', ''),
                    'timestamp': tx.get('timestamp', ''),
                    'operation_type': op_type,
                    'details': {}
                }
                
                # Convert Decimal to float and calculate totals
                for key, value in details.items():
                    if hasattr(value, '__float__'):
                        event['details'][key] = float(value)
                        
                        # Calculate totals based on operation type
                        if op_type == 'AddStockQuantity' and key == 'quantity_added':
                            totals['added'] += float(value)
                        elif op_type == 'SubtractStockQuantity' and key == 'quantity_subtracted':
                            totals['subtracted'] += float(value)
                        elif op_type == 'AddDefectiveGoods' and key == 'defective_quantity_added':
                            totals['defective_added'] += float(value)
                        elif op_type == 'SubtractDefectiveGoods' and key == 'defective_quantity_subtracted':
                            totals['defective_subtracted'] += float(value)
                    else:
                        event['details'][key] = value
                
                item_events.append(event)
        
        # Get production records that consumed this item
        production_records = dynamodb_service.scan_table('push_to_production')
        for record in production_records:
            components = record.get('components', [])
            for component in components:
                if component.get('item_id') == item_id:
                    consumed_qty = float(component.get('quantity_consumed', 0))
                    totals['consumed_by_production'] += consumed_qty
                    
                    # Add production event
                    item_events.append({
                        'transaction_id': record.get('production_id', ''),
                        'date': record.get('date', ''),
                        'timestamp': record.get('timestamp', ''),
                        'operation_type': 'ProductionConsumption',
                        'details': {
                            'item_id': item_id,
                            'quantity_consumed': consumed_qty,
                            'product_id': record.get('product_id', ''),
                            'product_name': record.get('product_name', ''),
                            'username': record.get('username', '')
                        }
                    })
        
        # Sort events
        reverse_order = order == "desc"
        item_events.sort(key=lambda x: x.get('timestamp', ''), reverse=reverse_order)
        
        payload = {
            "item_id": item_id,
            "date_from": date_from,
            "date_to": date_to,
            "count": len(item_events),
            "events": item_events,
            "totals": totals
        }
        
        return JsonResponse(payload)
        
    except Exception as e:
        logger.error(f"Error in get_item_history: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_monthly_inward_grid(request, body=None):
    """Get monthly inward grid - returns all materials like outward grid"""
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
        
        # 1) Determine first and last day of month
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        start_date_str = first_day.strftime("%Y-%m-%d")
        end_date_str = last_day.strftime("%Y-%m-%d")
        
        # 2) Fetch ALL Stock items first
        live_stock_map = {}
        stock_items = dynamodb_service.scan_table('STOCK')
        for item in stock_items:
            live_stock_map[item['item_id']] = {
                "current_qty": float(item.get('quantity', 0)),
                "group_id": item.get('group_id'),
                "name": item.get('name')
            }
        
        # 3) Get AddStockQuantity transactions for the month
        from boto3.dynamodb.conditions import Attr
        transactions = dynamodb_service.scan_table(
            'stock_transactions',
            FilterExpression=Attr('operation_type').eq('AddStockQuantity') & 
                           Attr('date').between(start_date_str, end_date_str)
        )
        
        # 4) Process inward transactions
        inward_data = defaultdict(lambda: {
            'inward_days': {},
            'total_inward': 0.0,
            'total_in_period_to_now': 0.0
        })
        
        # Get all AddStockQuantity transactions from month start to calculate opening balance
        all_inward_txns = dynamodb_service.scan_table(
            'stock_transactions',
            FilterExpression=Attr('operation_type').eq('AddStockQuantity') & 
                           Attr('date').gte(start_date_str)
        )
        
        # Process all inward transactions for opening balance calculation
        for txn in all_inward_txns:
            details = txn.get('details', {})
            item_id = details.get('item_id')
            if not item_id:
                continue
            quantity_added = float(details.get('quantity_added', 0))
            inward_data[item_id]['total_in_period_to_now'] += quantity_added
        
        # Process month-specific transactions for inward_days
        for txn in transactions:
            details = txn.get('details', {})
            item_id = details.get('item_id')
            if not item_id:
                continue
                
            # Extract day from date
            txn_date = txn.get('date', '')
            day = int(txn_date.split('-')[2]) if txn_date else 0
            
            quantity_added = float(details.get('quantity_added', 0))
            
            # Update inward data
            inward_data[item_id]['inward_days'][str(day)] = inward_data[item_id]['inward_days'].get(str(day), 0.0) + quantity_added
            inward_data[item_id]['total_inward'] += quantity_added
        
        # 5) Build response for ALL materials
        groups_data = dynamodb_service.scan_table('GROUPS')
        group_map = {g['group_id']: g.get('name', 'Unknown') for g in groups_data}
        
        final_output = defaultdict(list)
        monthly_total = 0.0
        
        for item_id, info in live_stock_map.items():
            data = inward_data[item_id]
            
            # Calculate opening balance: current_qty - total_inward_since_month_start
            opening_balance = info['current_qty'] - data['total_in_period_to_now']
            
            monthly_total += data['total_inward']
            
            item_entry = {
                "item_id": item_id,
                "item_name": info['name'],
                "opening_balance": round(opening_balance, 2),
                "inward_days": dict(data['inward_days']),
                "total_inward": round(data['total_inward'], 2)
            }
            
            grp_name = group_map.get(info['group_id'], "Ungrouped")
            final_output[grp_name].append(item_entry)
        
        # 6) Build payload
        payload = {
            "month": month_str,
            "type": "INWARD",
            "grid_data": dict(final_output),
            "monthly_total": monthly_total
        }
        
        return JsonResponse(payload, encoder=DecimalEncoder)
        
    except Exception as e:
        logger.error(f"Error in get_monthly_inward_grid: {e}", exc_info=True)
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_monthly_outward_grid(request, body=None):
    """Get monthly outward grid - optimized with GSI queries"""
    try:
        # Ensure index exists
        ensure_transactions_index()
        
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
        
        # 1) Determine first and last day of month
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        start_date_str = first_day.strftime("%Y-%m-%d")
        end_date_str = last_day.strftime("%Y-%m-%d")
        
        # 2) Fetch LIVE Stock
        live_stock_map = {}
        stock_items = dynamodb_service.scan_table('STOCK')
        for item in stock_items:
            live_stock_map[item['item_id']] = {
                "current_qty": float(item.get('quantity', 0)),
                "group_id": item.get('group_id'),
                "name": item.get('name')
            }
        
        # 3) OPTIMIZED FETCH: Query specific operations via Index
        import boto3
        dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
        tx_tbl = dynamodb.Table('stock_transactions')
        txns = []
        
        # List of operations we need for the O/B Math
        required_ops = ["AddStockQuantity", "PushToProduction", "AddDefectiveGoods"]
        
        for op in required_ops:
            try:
                # Query GSI: operation_type = op AND date >= start_date
                query_params = {
                    'IndexName': 'OpTypeDateIndex',
                    'KeyConditionExpression': Key('operation_type').eq(op) & Key('date').gte(start_date_str)
                }
                
                resp = tx_tbl.query(**query_params)
                txns.extend(resp.get("Items", []))
                
                while 'LastEvaluatedKey' in resp:
                    query_params['ExclusiveStartKey'] = resp['LastEvaluatedKey']
                    resp = tx_tbl.query(**query_params)
                    txns.extend(resp.get("Items", []))
            except Exception as query_error:
                logger.warning(f"GSI query failed for {op}, falling back to scan: {query_error}")
                # Fallback to scan if GSI not ready
                fallback_txns = dynamodb_service.scan_table(
                    'stock_transactions',
                    FilterExpression=Attr('operation_type').eq(op) & Attr('date').gte(start_date_str)
                )
                txns.extend(fallback_txns)
        
        # 4) Process Data
        report_data = defaultdict(lambda: {
            "out_days": defaultdict(float),
            "total_in_period_to_now": 0.0,
            "total_out_period_to_now": 0.0,
            "total_out_month": 0.0
        })
        
        for tx in txns:
            tx_date_str = tx.get('date')
            try:
                day_num = datetime.strptime(tx_date_str, "%Y-%m-%d").date().day
            except:
                continue
            
            is_in_view_month = (start_date_str <= tx_date_str <= end_date_str)
            op_type = tx.get('operation_type')
            details = tx.get('details', {})
            
            if op_type == "AddStockQuantity":
                item_id = details.get('item_id')
                report_data[item_id]["total_in_period_to_now"] += float(details.get('quantity_added', 0))
            
            elif op_type in ["PushToProduction", "AddDefectiveGoods"]:
                if op_type == "PushToProduction":
                    deductions = details.get('deductions', {})
                    for item_id, qty_dec in deductions.items():
                        qty = float(qty_dec)
                        report_data[item_id]["total_out_period_to_now"] += qty
                        if is_in_view_month:
                            report_data[item_id]["out_days"][str(day_num)] += qty
                            report_data[item_id]["total_out_month"] += qty
                else:
                    item_id = details.get('item_id')
                    qty = float(details.get('defective_added', 0))
                    report_data[item_id]["total_out_period_to_now"] += qty
                    if is_in_view_month:
                        report_data[item_id]["out_days"][str(day_num)] += qty
                        report_data[item_id]["total_out_month"] += qty
        
        # 5) Build Response with groups
        groups_data = dynamodb_service.scan_table('GROUPS')
        group_map = {g['group_id']: g.get('name', 'Unknown') for g in groups_data}
        
        final_output = defaultdict(list)
        monthly_total = 0.0
        
        for item_id, info in live_stock_map.items():
            data = report_data[item_id]
            # O/B Formula
            opening_balance = info['current_qty'] - data["total_in_period_to_now"] + data["total_out_period_to_now"]
            
            monthly_total += data["total_out_month"]
            
            item_entry = {
                "item_id": item_id,
                "item_name": info['name'],
                "opening_balance": round(opening_balance, 2),
                "outward_days": dict(data["out_days"]),
                "total_outward": round(data["total_out_month"], 2)
            }
            grp_name = group_map.get(info['group_id'], "Ungrouped")
            final_output[grp_name].append(item_entry)
        
        # 6) Build payload
        payload = {
            "month": month_str,
            "type": "OUTWARD",
            "grid_data": dict(final_output),
            "monthly_total": monthly_total
        }
        
        return JsonResponse(payload, encoder=DecimalEncoder)
        
    except Exception as e:
        logger.error(f"Error in get_monthly_outward_grid: {e}", exc_info=True)
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)