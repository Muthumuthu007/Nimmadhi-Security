"""
Optimized normal report functions with batch operations and caching
"""
import json
import calendar
from decimal import Decimal
from datetime import datetime, timedelta, date
from collections import defaultdict
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from backend.dynamodb_service import dynamodb_service
from boto3.dynamodb.conditions import Attr
import logging

logger = logging.getLogger(__name__)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)

def extract_consumption_details(transactions):
    details = []
    for tx in transactions:
        op = tx.get('operation_type')
        if op == 'PushToProduction':
            d = tx.get('details', {})
            for item_id, qty in d.get('deductions', {}).items():
                details.append({
                    'item_id': item_id,
                    'quantity_consumed': Decimal(str(qty)),
                    'timestamp': tx.get('timestamp', '')
                })
        elif op == 'AddDefectiveGoods':
            d = tx.get('details', {})
            details.append({
                'item_id': d.get('item_id', 'Unknown'),
                'quantity_consumed': Decimal(str(d.get('defective_added', 0))),
                'timestamp': tx.get('timestamp', '')
            })
    return details

def compute_item_rows_and_totals(start_date, end_date):
    """Optimized computation with batch operations"""
    # Batch get all stock items
    stock_items = dynamodb_service.scan_table('STOCK')
    stock_map = {it['item_id']: Decimal(str(it.get('cost_per_unit', 0))) for it in stock_items}
    
    # Get transactions in range
    txns = dynamodb_service.scan_table(
        'stock_transactions',
        FilterExpression=Attr('date').between(start_date, end_date)
    )
    
    # Process inward
    inward_map = defaultdict(Decimal)
    for t in txns:
        if t.get('operation_type') == 'AddStockQuantity':
            details = t.get('details', {})
            item_id = details.get('item_id')
            qty_added = Decimal(str(details.get('quantity_added', 0)))
            inward_map[item_id] += qty_added
    
    # Process consumption
    consumption_details = extract_consumption_details(txns)
    consumption_map = defaultdict(Decimal)
    for d in consumption_details:
        consumption_map[d['item_id']] += d['quantity_consumed']
    
    # Get opening stock
    opening_map = defaultdict(lambda: Decimal('0'))
    opening_txns = dynamodb_service.scan_table(
        'stock_transactions',
        FilterExpression=Attr('operation_type').eq('SaveOpeningStock') & Attr('date').eq(start_date)
    )
    if opening_txns:
        opening_record = min(opening_txns, key=lambda x: x.get('timestamp', ''))
        for entry in opening_record.get('details', {}).get('per_item_opening', []):
            item_id = entry.get('item_id')
            opening_qty = Decimal(str(entry.get('opening_qty', 0)))
            opening_map[item_id] = opening_qty
    
    # Build rows
    rows = []
    for it in stock_items:
        item_id = it.get('item_id')
        rate = stock_map[item_id]
        open_qty = opening_map.get(item_id, Decimal('0'))
        open_amt = rate * open_qty
        in_qty = inward_map.get(item_id, Decimal('0'))
        in_amt = in_qty * rate
        cons_qty = consumption_map.get(item_id, Decimal('0'))
        cons_amt = cons_qty * rate
        bal_qty = (open_qty + in_qty) - cons_qty
        bal_amt = bal_qty * rate
        
        rows.append({
            'description': item_id,
            'rate': float(rate),
            'opening_stock_qty': int(open_qty),
            'opening_stock_amount': float(open_amt),
            'inward_qty': int(in_qty),
            'inward_amount': float(in_amt),
            'consumption_qty': int(cons_qty),
            'consumption_amount': float(cons_amt),
            'balance_qty': int(bal_qty),
            'balance_amount': float(bal_amt),
        })
    
    totals = {
        'total_opening_stock_qty': sum(r['opening_stock_qty'] for r in rows),
        'total_opening_stock_amount': sum(r['opening_stock_amount'] for r in rows),
        'total_inward_qty': sum(r['inward_qty'] for r in rows),
        'total_inward_amount': sum(r['inward_amount'] for r in rows),
        'total_consumption_qty': sum(r['consumption_qty'] for r in rows),
        'total_consumption_amount': sum(r['consumption_amount'] for r in rows),
        'total_balance_qty': sum(r['balance_qty'] for r in rows),
        'total_balance_amount': sum(r['balance_amount'] for r in rows),
    }
    
    return rows, totals

def build_transactions_section(start_date, end_date):
    """Optimized transaction section building"""
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Get all transactions in range at once
    txns = dynamodb_service.scan_table(
        'stock_transactions',
        FilterExpression=Attr('date').between(start_date, end_date)
    )
    
    # Group by date
    txns_by_date = defaultdict(list)
    for tx in txns:
        tx_date = tx.get('date')
        if tx_date:
            details = tx.get('details')
            if isinstance(details, dict):
                details.pop('per_item_opening', None)
                details.pop('per_item_closing', None)
            txns_by_date[tx_date].append(tx)
    
    # Build section
    tx_section = {}
    for n in range((end_dt - start_dt).days + 1):
        day = (start_dt + timedelta(days=n)).strftime('%Y-%m-%d')
        txs = txns_by_date.get(day, [])
        
        inward_qty = inward_amt = consumed_qty = consumed_amt = balance_qty = balance_amt = 0
        
        for tx in txs:
            op = tx.get('operation_type', '') or tx.get('operation', '')
            qty = float(tx.get('qty', 0))
            amt = float(tx.get('amount', 0.0))
            
            if op == 'Inward':
                inward_qty += qty
                inward_amt += amt
            elif op == 'Consume':
                consumed_qty += qty
                consumed_amt += amt
            elif op == 'SaveClosingStock':
                balance_qty += qty
                balance_amt += amt
        
        tx_section[day] = {
            'operations': txs,
            'inward_qty': inward_qty,
            'inward_amount': inward_amt,
            'consumption_qty': consumed_qty,
            'consumption_amount': consumed_amt,
            'balance_qty': balance_qty,
            'balance_amount': balance_amt
        }
    
    return tx_section

def enrich_with_groups(items):
    """Batch enrich items with group information"""
    # Get cached groups
    cache_key = "all_groups_stock_map"
    cached = cache.get(cache_key)
    
    if cached:
        stock_items, groups = cached
    else:
        stock_items = dynamodb_service.scan_table('STOCK')
        groups = dynamodb_service.scan_table('GROUPS')
        cache.set(cache_key, (stock_items, groups), 600)
    
    name_to_group_id = {
        item['name'].strip().lower(): item.get('group_id')
        for item in stock_items if 'name' in item and 'group_id' in item
    }
    
    group_id_to_name = {g['group_id']: g.get('name', 'Unknown') for g in groups}
    group_id_to_parent = {g['group_id']: g.get('parent_id') for g in groups}
    
    for item in items:
        desc = item.get('description', '').strip().lower()
        group_id = name_to_group_id.get(desc)
        group_name = group_id_to_name.get(group_id, 'Unknown') if group_id else 'Unknown'
        parent_group_id = group_id_to_parent.get(group_id)
        parent_group_name = group_id_to_name.get(parent_group_id, 'Unknown') if parent_group_id else group_name
        
        item['group_id'] = group_id
        item['group_name'] = group_name
        item['parent_group_id'] = parent_group_id
        item['parent_group_name'] = parent_group_name

def build_summaries(items):
    """Build subgroup and main group summaries"""
    subgroup_totals = {}
    for item in items:
        subgroup_name = item['group_name']
        if subgroup_name not in subgroup_totals:
            subgroup_totals[subgroup_name] = {
                'description': f'TOTAL: {subgroup_name}',
                'opening_stock_qty': 0, 'opening_stock_amount': 0.0,
                'inward_qty': 0, 'inward_amount': 0.0,
                'consumption_qty': 0, 'consumption_amount': 0.0,
                'balance_qty': 0, 'balance_amount': 0.0
            }
        sub = subgroup_totals[subgroup_name]
        sub['opening_stock_qty'] += item.get('opening_stock_qty', 0)
        sub['opening_stock_amount'] += float(item.get('opening_stock_amount', 0.0))
        sub['inward_qty'] += item.get('inward_qty', 0)
        sub['inward_amount'] += float(item.get('inward_amount', 0.0))
        sub['consumption_qty'] += item.get('consumption_qty', 0)
        sub['consumption_amount'] += float(item.get('consumption_amount', 0.0))
        sub['balance_qty'] += item.get('balance_qty', 0)
        sub['balance_amount'] += float(item.get('balance_amount', 0.0))
    
    items_with_totals = []
    sub_grouped_items = defaultdict(list)
    for item in items:
        sub_grouped_items[item['group_name']].append(item)
    
    for subgroup_name, subgroup_items in sub_grouped_items.items():
        items_with_totals.extend(subgroup_items)
        items_with_totals.append(subgroup_totals[subgroup_name])
    
    main_group_summary = {}
    for item in items:
        main_group_name = item['parent_group_name']
        if main_group_name not in main_group_summary:
            main_group_summary[main_group_name] = {
                'description': main_group_name,
                'opening_stock_qty': 0, 'opening_stock_amount': 0.0,
                'inward_qty': 0, 'inward_amount': 0.0,
                'consumption_qty': 0, 'consumption_amount': 0.0,
                'balance_qty': 0, 'balance_amount': 0.0
            }
        g = main_group_summary[main_group_name]
        g['opening_stock_qty'] += item.get('opening_stock_qty', 0)
        g['opening_stock_amount'] += float(item.get('opening_stock_amount', 0.0))
        g['inward_qty'] += item.get('inward_qty', 0)
        g['inward_amount'] += float(item.get('inward_amount', 0.0))
        g['consumption_qty'] += item.get('consumption_qty', 0)
        g['consumption_amount'] += float(item.get('consumption_amount', 0.0))
        g['balance_qty'] += item.get('balance_qty', 0)
        g['balance_amount'] += float(item.get('balance_amount', 0.0))
    
    group_summary_list = list(main_group_summary.values())
    
    if group_summary_list:
        total_row = {
            'description': 'TOTAL',
            'opening_stock_qty': sum(g['opening_stock_qty'] for g in group_summary_list),
            'opening_stock_amount': sum(g['opening_stock_amount'] for g in group_summary_list),
            'inward_qty': sum(g['inward_qty'] for g in group_summary_list),
            'inward_amount': sum(g['inward_amount'] for g in group_summary_list),
            'consumption_qty': sum(g['consumption_qty'] for g in group_summary_list),
            'consumption_amount': sum(g['consumption_amount'] for g in group_summary_list),
            'balance_qty': sum(g['balance_qty'] for g in group_summary_list),
            'balance_amount': sum(g['balance_amount'] for g in group_summary_list)
        }
        group_summary_list.append(total_row)
    
    return items_with_totals, group_summary_list

@csrf_exempt
@require_http_methods(['POST'])
def get_daily_report(request):
    try:
        body = json.loads(request.body) if request.body else {}
        rd = body.get('report_date')
        if rd is None:
            rd = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d')
        rd = rd.strip()
        
        cache_key = f"normal_daily_{rd}"
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse(cached, encoder=DecimalEncoder)
        
        items, _ = compute_item_rows_and_totals(rd, rd)
        tx_section = build_transactions_section(rd, rd)
        enrich_with_groups(items)
        items_with_totals, group_summary_list = build_summaries(items)
        
        payload = {
            'report_period': {'start_date': rd, 'end_date': rd},
            'items': items_with_totals,
            'transactions': tx_section,
            'group_summary': group_summary_list
        }
        
        cache.set(cache_key, payload, 300)
        return JsonResponse(payload, encoder=DecimalEncoder)
    
    except Exception as e:
        logger.error(f'Error in get_daily_report: {e}', exc_info=True)
        return JsonResponse({'error': f'Internal error: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def get_weekly_report(request):
    try:
        body = json.loads(request.body) if request.body else {}
        now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        ed = body.get('end_date', now.strftime('%Y-%m-%d')).strip()
        sd = body.get('start_date', (now - timedelta(days=7)).strftime('%Y-%m-%d')).strip()
        
        cache_key = f"normal_weekly_{sd}_{ed}"
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse(cached, encoder=DecimalEncoder)
        
        items, _ = compute_item_rows_and_totals(sd, ed)
        tx_section = build_transactions_section(sd, ed)
        enrich_with_groups(items)
        items_with_totals, group_summary_list = build_summaries(items)
        
        payload = {
            'report_period': {'start_date': sd, 'end_date': ed},
            'items': items_with_totals,
            'transactions': tx_section,
            'group_summary': group_summary_list
        }
        
        cache.set(cache_key, payload, 300)
        return JsonResponse(payload, encoder=DecimalEncoder)
    
    except Exception as e:
        logger.error(f'Error in get_weekly_report: {e}', exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def get_monthly_report(request):
    try:
        body = json.loads(request.body) if request.body else {}
        m = body.get('month')
        if not isinstance(m, str):
            return JsonResponse({'error': "'month' must be a string in YYYY-MM"}, status=400)
        m = m.strip()
        
        try:
            yr, mo = map(int, m.split('-'))
        except ValueError:
            return JsonResponse({'error': "'month' must be in YYYY-MM"}, status=400)
        
        cache_key = f"normal_monthly_{m}"
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse(cached, encoder=DecimalEncoder)
        
        first = date(yr, mo, 1)
        last = date(yr, mo, calendar.monthrange(yr, mo)[1])
        sd, ed = first.strftime('%Y-%m-%d'), last.strftime('%Y-%m-%d')
        
        items, _ = compute_item_rows_and_totals(sd, ed)
        enrich_with_groups(items)
        items_with_totals, group_summary_list = build_summaries(items)
        
        payload = {
            'report_period': {'start_date': sd, 'end_date': ed},
            'items': items_with_totals,
            'group_summary': group_summary_list
        }
        
        cache.set(cache_key, payload, 600)
        return JsonResponse(payload, encoder=DecimalEncoder)
    
    except Exception as e:
        logger.error(f'Error in get_monthly_report: {e}', exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
