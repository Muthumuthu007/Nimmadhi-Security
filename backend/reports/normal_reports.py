"""
Normal report functions - exact Lambda implementation
"""
import json
import boto3
import calendar
from boto3.dynamodb.conditions import Attr, Key
from decimal import Decimal
from datetime import datetime, timedelta, date
from collections import defaultdict
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

dynamodb = boto3.resource('dynamodb', region_name=settings.AWS_REGION)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)

def get_group_chain(group_id):
    chain = []
    tbl = dynamodb.Table('Groups')
    while group_id:
        resp = tbl.get_item(Key={'group_id': group_id})
        if 'Item' not in resp:
            break
        grp = resp['Item']
        chain.insert(0, grp['name'])
        group_id = grp.get('parent_id')
    return chain

def _get_stock_map():
    tbl = dynamodb.Table('stock')
    resp = tbl.scan()
    stock_map = {}
    items = resp.get('Items', [])
    while 'LastEvaluatedKey' in resp:
        resp = tbl.scan(ExclusiveStartKey=resp['LastEvaluatedKey'])
        items.extend(resp.get('Items', []))
    for it in items:
        stock_map[it['item_id']] = Decimal(str(it.get('cost_per_unit', 0)))
    return stock_map

def _date_list(start_date_str, end_date_str):
    start_dt = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    out = []
    cur = start_dt
    while cur <= end_dt:
        out.append(cur.strftime('%Y-%m-%d'))
        cur += timedelta(days=1)
    return out

def _fetch_transactions_in_range(start_date_str, end_date_str):
    tbl = dynamodb.Table('stock_transactions')
    resp = tbl.scan(FilterExpression=Attr('date').between(start_date_str, end_date_str))
    all_txns = resp.get('Items', [])
    while 'LastEvaluatedKey' in resp:
        resp = tbl.scan(
            FilterExpression=Attr('date').between(start_date_str, end_date_str),
            ExclusiveStartKey=resp['LastEvaluatedKey']
        )
        all_txns.extend(resp.get('Items', []))
    return all_txns

def extract_consumption_details(transactions):
    ops = ['AddDefectiveGoods', 'PushToProduction']
    details = []
    for tx in transactions:
        op = tx.get('operation_type')
        if op in ops:
            d = tx.get('details', {})
            if op == 'PushToProduction':
                for item_id, qty in d.get('deductions', {}).items():
                    details.append({
                        'item_id': item_id,
                        'quantity_consumed': Decimal(str(qty)),
                        'timestamp': tx.get('timestamp', '')
                    })
            else:
                details.append({
                    'item_id': d.get('item_id', 'Unknown'),
                    'quantity_consumed': Decimal(str(d.get('defective_added', 0))),
                    'timestamp': tx.get('timestamp', '')
                })
    return details

def get_existing_stock_record(operation, report_date):
    try:
        tbl = dynamodb.Table('stock_transactions')
        resp = tbl.scan(FilterExpression=Attr('operation_type').eq(operation) & Attr('date').eq(report_date))
        items = resp.get('Items', [])
        if items:
            return min(items, key=lambda x: x.get('timestamp', ''))
        return None
    except Exception as e:
        logger.error(f'get_existing_stock_record error: {e}')
        return None

def compute_item_rows_and_totals(start_date, end_date):
    stock_tbl = dynamodb.Table('stock')
    resp = stock_tbl.scan()
    stock_items = resp.get('Items', [])
    while 'LastEvaluatedKey' in resp:
        resp = stock_tbl.scan(ExclusiveStartKey=resp['LastEvaluatedKey'])
        stock_items.extend(resp.get('Items', []))

    txns = _fetch_transactions_in_range(start_date, end_date)

    inward_map = defaultdict(Decimal)
    for t in txns:
        if t.get('operation_type') == 'AddStockQuantity':
            details = t.get('details', {})
            item_id = details.get('item_id')
            qty_added = Decimal(str(details.get('quantity_added', 0)))
            inward_map[item_id] += qty_added

    consumption_details = extract_consumption_details(txns)
    consumption_map = defaultdict(Decimal)
    for d in consumption_details:
        consumption_map[d['item_id']] += d['quantity_consumed']

    opening_map = defaultdict(lambda: Decimal('0'))
    opening_record = get_existing_stock_record('SaveOpeningStock', start_date)
    if opening_record:
        for entry in opening_record.get('details', {}).get('per_item_opening', []):
            item_id = entry.get('item_id')
            opening_qty = Decimal(str(entry.get('opening_qty', 0)))
            opening_map[item_id] = opening_qty

    stock_map = {}
    for it in stock_items:
        stock_map[it['item_id']] = Decimal(str(it.get('cost_per_unit', 0)))

    rows = []
    for it in stock_items:
        item_id = it.get('item_id')
        rate = Decimal(str(it.get('cost_per_unit', 0)))
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

def _build_transactions_section_without_opening(start_date, end_date):
    tx_table = dynamodb.Table('stock_transactions')
    tx_section = {}
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')

    for n in range((end_dt - start_dt).days + 1):
        day = (start_dt + timedelta(days=n)).strftime('%Y-%m-%d')
        response = tx_table.scan(FilterExpression=Attr('date').eq(day))
        txs = response.get('Items', [])

        for tx in txs:
            details = tx.get('details')
            if isinstance(details, dict):
                details.pop('per_item_opening', None)
                details.pop('per_item_closing', None)

        inward_qty = 0
        inward_amt = 0
        consumed_qty = 0
        consumed_amt = 0
        balance_qty = 0
        balance_amt = 0

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

@csrf_exempt
@require_http_methods(['POST'])
def get_daily_report(request):
    try:
        body = json.loads(request.body) if request.body else {}
        rd = body.get('report_date')
        if rd is None:
            rd = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d')
        elif not isinstance(rd, str):
            return JsonResponse({'error': 'report_date must be a string'}, status=400)
        rd = rd.strip()

        items, _ = compute_item_rows_and_totals(rd, rd)
        tx_section = _build_transactions_section_without_opening(rd, rd)

        stock_table = dynamodb.Table('stock')
        stock_items = stock_table.scan().get('Items', [])
        name_to_group_id = {
            item['name'].strip().lower(): item.get('group_id')
            for item in stock_items
            if 'name' in item and 'group_id' in item
        }

        groups_table = dynamodb.Table('Groups')
        group_items = groups_table.scan().get('Items', [])
        group_id_to_name = {}
        group_id_to_parent = {}

        for group in group_items:
            gid = group['group_id']
            group_id_to_name[gid] = group.get('name', 'Unknown')
            group_id_to_parent[gid] = group.get('parent_id')

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

        subgroup_totals = {}
        for item in items:
            subgroup_name = item['group_name']
            if subgroup_name not in subgroup_totals:
                subgroup_totals[subgroup_name] = {
                    'description': f'TOTAL: {subgroup_name}',
                    'opening_stock_qty': 0,
                    'opening_stock_amount': 0.0,
                    'inward_qty': 0,
                    'inward_amount': 0.0,
                    'consumption_qty': 0,
                    'consumption_amount': 0.0,
                    'balance_qty': 0,
                    'balance_amount': 0.0
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
                    'opening_stock_qty': 0,
                    'opening_stock_amount': 0.0,
                    'inward_qty': 0,
                    'inward_amount': 0.0,
                    'consumption_qty': 0,
                    'consumption_amount': 0.0,
                    'balance_qty': 0,
                    'balance_amount': 0.0
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

        total_row = {
            'description': 'TOTAL',
            'opening_stock_qty': 0,
            'opening_stock_amount': 0.0,
            'inward_qty': 0,
            'inward_amount': 0.0,
            'consumption_qty': 0,
            'consumption_amount': 0.0,
            'balance_qty': 0,
            'balance_amount': 0.0
        }
        for group in group_summary_list:
            total_row['opening_stock_qty'] += group['opening_stock_qty']
            total_row['opening_stock_amount'] += group['opening_stock_amount']
            total_row['inward_qty'] += group['inward_qty']
            total_row['inward_amount'] += group['inward_amount']
            total_row['consumption_qty'] += group['consumption_qty']
            total_row['consumption_amount'] += group['consumption_amount']
            total_row['balance_qty'] += group['balance_qty']
            total_row['balance_amount'] += group['balance_amount']

        group_summary_list.append(total_row)

        payload = {
            'report_period': {'start_date': rd, 'end_date': rd},
            'items': items_with_totals,
            'transactions': tx_section,
            'group_summary': group_summary_list
        }

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

        items, _ = compute_item_rows_and_totals(sd, ed)
        tx_section = _build_transactions_section_without_opening(sd, ed)

        stock_table = dynamodb.Table('stock')
        stocks = stock_table.scan().get('Items', [])
        name_to_group = {s['name'].strip().lower(): s.get('group_id') for s in stocks if 'name' in s}

        groups_table = dynamodb.Table('Groups')
        groups = groups_table.scan().get('Items', [])
        group_name_map = {g['group_id']: g.get('name', 'Unknown') for g in groups}
        group_parent_map = {g['group_id']: g.get('parent_id') for g in groups}

        for item in items:
            desc = item.get('description', '').strip().lower()
            gid = name_to_group.get(desc)
            gname = group_name_map.get(gid, 'Unknown') if gid else 'Unknown'
            pgid = group_parent_map.get(gid)
            pgname = group_name_map.get(pgid, gname) if pgid else gname
            item.update({
                'group_id': gid,
                'group_name': gname,
                'parent_group_id': pgid,
                'parent_group_name': pgname
            })

        subgroup_totals = {}
        for it in items:
            sub = it['group_name']
            if sub not in subgroup_totals:
                subgroup_totals[sub] = {k: 0 if isinstance(v, int) else 0.0
                                         for k, v in it.items() if k.endswith('_qty') or k.endswith('_amount')}
                subgroup_totals[sub]['description'] = f'TOTAL: {sub}'
            tot = subgroup_totals[sub]
            tot['opening_stock_qty'] += it.get('opening_stock_qty', 0)
            tot['opening_stock_amount'] += float(it.get('opening_stock_amount', 0.0))
            tot['inward_qty'] += it.get('inward_qty', 0)
            tot['inward_amount'] += float(it.get('inward_amount', 0.0))
            tot['consumption_qty'] += it.get('consumption_qty', 0)
            tot['consumption_amount'] += float(it.get('consumption_amount', 0.0))
            tot['balance_qty'] += it.get('balance_qty', 0)
            tot['balance_amount'] += float(it.get('balance_amount', 0.0))

        items_with_totals = []
        by_sub = defaultdict(list)
        for it in items:
            by_sub[it['group_name']].append(it)
        for sub, group_items in by_sub.items():
            items_with_totals.extend(group_items)
            items_with_totals.append(subgroup_totals[sub])

        main_summary = {}
        for it in items:
            mg = it['parent_group_name']
            if mg not in main_summary:
                main_summary[mg] = {k: 0 if isinstance(v, int) else 0.0
                                     for k, v in it.items() if k.endswith('_qty') or k.endswith('_amount')}
                main_summary[mg]['description'] = mg
            g = main_summary[mg]
            g['opening_stock_qty'] += it.get('opening_stock_qty', 0)
            g['opening_stock_amount'] += float(it.get('opening_stock_amount', 0.0))
            g['inward_qty'] += it.get('inward_qty', 0)
            g['inward_amount'] += float(it.get('inward_amount', 0.0))
            g['consumption_qty'] += it.get('consumption_qty', 0)
            g['consumption_amount'] += float(it.get('consumption_amount', 0.0))
            g['balance_qty'] += it.get('balance_qty', 0)
            g['balance_amount'] += float(it.get('balance_amount', 0.0))

        group_summary_list = list(main_summary.values())
        grand = {k: 0 if isinstance(v, int) else 0.0 for k, v in group_summary_list[0].items()}
        grand['description'] = 'TOTAL'
        for g in group_summary_list:
            grand['opening_stock_qty'] += g['opening_stock_qty']
            grand['opening_stock_amount'] += g['opening_stock_amount']
            grand['inward_qty'] += g['inward_qty']
            grand['inward_amount'] += g['inward_amount']
            grand['consumption_qty'] += g['consumption_qty']
            grand['consumption_amount'] += g['consumption_amount']
            grand['balance_qty'] += g['balance_qty']
            grand['balance_amount'] += g['balance_amount']
        group_summary_list.append(grand)

        payload = {
            'report_period': {'start_date': sd, 'end_date': ed},
            'items': items_with_totals,
            'transactions': tx_section,
            'group_summary': group_summary_list
        }
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

        first = date(yr, mo, 1)
        last = date(yr, mo, calendar.monthrange(yr, mo)[1])
        sd, ed = first.strftime('%Y-%m-%d'), last.strftime('%Y-%m-%d')

        items, _ = compute_item_rows_and_totals(sd, ed)

        stock_tbl = dynamodb.Table('stock')
        stocks = stock_tbl.scan().get('Items', [])
        name_to_group = {s['name'].strip().lower(): s.get('group_id') for s in stocks if 'name' in s}

        groups_tbl = dynamodb.Table('Groups')
        groups = groups_tbl.scan().get('Items', [])
        gid_to_name = {g['group_id']: g.get('name', 'Unknown') for g in groups}
        gid_to_parent = {g['group_id']: g.get('parent_id') for g in groups}

        for it in items:
            desc = it.get('description', '').strip().lower()
            gid = name_to_group.get(desc)
            gname = gid_to_name.get(gid, 'Unknown') if gid else 'Unknown'
            pgid = gid_to_parent.get(gid)
            pgname = gid_to_name.get(pgid, gname) if pgid else gname
            it.update({
                'group_id': gid,
                'group_name': gname,
                'parent_group_id': pgid,
                'parent_group_name': pgname
            })

        subgroup_totals = {}
        for it in items:
            sub = it['group_name']
            if sub not in subgroup_totals:
                subgroup_totals[sub] = {
                    k: (0 if isinstance(v, int) else 0.0)
                    for k, v in it.items()
                    if k.endswith('_qty') or k.endswith('_amount')
                }
                subgroup_totals[sub]['description'] = f'TOTAL: {sub}'
            tot = subgroup_totals[sub]
            tot['opening_stock_qty'] += it.get('opening_stock_qty', 0)
            tot['opening_stock_amount'] += float(it.get('opening_stock_amount', 0.0))
            tot['inward_qty'] += it.get('inward_qty', 0)
            tot['inward_amount'] += float(it.get('inward_amount', 0.0))
            tot['consumption_qty'] += it.get('consumption_qty', 0)
            tot['consumption_amount'] += float(it.get('consumption_amount', 0.0))
            tot['balance_qty'] += it.get('balance_qty', 0)
            tot['balance_amount'] += float(it.get('balance_amount', 0.0))

        items_with_totals = []
        by_sub = defaultdict(list)
        for it in items:
            by_sub[it['group_name']].append(it)
        for sub, grp_items in by_sub.items():
            items_with_totals.extend(grp_items)
            items_with_totals.append(subgroup_totals[sub])

        main_summary = {}
        for it in items:
            mg = it['parent_group_name']
            if mg not in main_summary:
                main_summary[mg] = {
                    k: (0 if isinstance(v, int) else 0.0)
                    for k, v in it.items()
                    if k.endswith('_qty') or k.endswith('_amount')
                }
                main_summary[mg]['description'] = mg
            g = main_summary[mg]
            g['opening_stock_qty'] += it.get('opening_stock_qty', 0)
            g['opening_stock_amount'] += float(it.get('opening_stock_amount', 0.0))
            g['inward_qty'] += it.get('inward_qty', 0)
            g['inward_amount'] += float(it.get('inward_amount', 0.0))
            g['consumption_qty'] += it.get('consumption_qty', 0)
            g['consumption_amount'] += float(it.get('consumption_amount', 0.0))
            g['balance_qty'] += it.get('balance_qty', 0)
            g['balance_amount'] += float(it.get('balance_amount', 0.0))

        group_summary_list = list(main_summary.values())
        if group_summary_list:
            grand = {
                k: (0 if isinstance(v, int) else 0.0)
                for k, v in group_summary_list[0].items()
            }
            grand['description'] = 'TOTAL'
            for g in group_summary_list:
                grand['opening_stock_qty'] += g['opening_stock_qty']
                grand['opening_stock_amount'] += g['opening_stock_amount']
                grand['inward_qty'] += g['inward_qty']
                grand['inward_amount'] += g['inward_amount']
                grand['consumption_qty'] += g['consumption_qty']
                grand['consumption_amount'] += g['consumption_amount']
                grand['balance_qty'] += g['balance_qty']
                grand['balance_amount'] += g['balance_amount']
            group_summary_list.append(grand)

        payload = {
            'report_period': {'start_date': sd, 'end_date': ed},
            'items': items_with_totals,
            'group_summary': group_summary_list
        }
        return JsonResponse(payload, encoder=DecimalEncoder)

    except Exception as e:
        logger.error(f'Error in get_monthly_report: {e}', exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
