import json
import boto3
from boto3.dynamodb.conditions import Attr
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def get_daily_consumption_summary(request):
    """Get daily consumption summary - Direct boto3 like Lambda"""
    try:
        body = json.loads(request.body)
        
        # 1) Determine report_date (IST)
        report_date = body.get("report_date")
        if not report_date:
            report_date = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")
        report_date = report_date.strip()

        # 2) Load all transactions - Direct boto3
        dynamodb = boto3.resource('dynamodb', region_name=settings.AWS_REGION)
        tx_tbl = dynamodb.Table('stock_transactions')
        tx_resp = tx_tbl.scan(FilterExpression=Attr('date').eq(report_date))
        transactions = tx_resp.get('Items', [])
        while 'LastEvaluatedKey' in tx_resp:
            tx_resp = tx_tbl.scan(
                FilterExpression=Attr('date').eq(report_date),
                ExclusiveStartKey=tx_resp['LastEvaluatedKey']
            )
            transactions.extend(tx_resp.get('Items', []))

        # 3) Extract consumption - Exact Lambda logic
        summary_map = defaultdict(Decimal)
        for tx in transactions:
            op = tx.get('operation_type')
            if op in ['AddDefectiveGoods', 'PushToProduction']:
                d = tx.get('details', {})
                if op == 'PushToProduction':
                    for item_id, qty in d.get('deductions', {}).items():
                        summary_map[item_id] += Decimal(str(qty))
                else:  # AddDefectiveGoods
                    item_id = d.get('item_id', 'Unknown')
                    qty = d.get('defective_added', 0)
                    summary_map[item_id] += Decimal(str(qty))

        # 4) Get stock and groups
        stock_tbl = dynamodb.Table('stock')
        groups_tbl = dynamodb.Table('Groups')
        
        def get_group_chain(group_id):
            chain = []
            while group_id:
                resp = groups_tbl.get_item(Key={'group_id': group_id})
                if 'Item' not in resp:
                    break
                grp = resp['Item']
                chain.insert(0, grp['name'])
                group_id = grp.get('parent_id')
            return chain
        
        # 5) Build nested structure
        nested = {}
        total_amt = Decimal('0')
        
        for item_id, qty in summary_map.items():
            # Get stock item
            stock_resp = stock_tbl.get_item(Key={'item_id': item_id})
            if 'Item' in stock_resp:
                stock_item = stock_resp['Item']
                group_id = stock_item.get('group_id')
                
                # Get group chain
                chain = get_group_chain(group_id) if group_id else []
                group = chain[0] if len(chain) >= 1 else 'Unknown'
                subgroup = chain[1] if len(chain) >= 2 else 'Unknown'
                
                # Add to nested structure
                nested.setdefault(group, {}).setdefault(subgroup, []).append({
                    'item_id': item_id,
                    'total_quantity_consumed': float(qty)
                })
                
                # Calculate amount
                rate = Decimal(str(stock_item.get('cost_per_unit', 0)))
                total_amt += rate * qty
            else:
                # Unknown item
                nested.setdefault('Unknown', {}).setdefault('Unknown', []).append({
                    'item_id': item_id,
                    'total_quantity_consumed': float(qty)
                })

        # 6) Build response
        total_qty = sum(summary_map.values())
        payload = {
            'report_date': report_date,
            'consumption_summary': nested,
            'total_consumption_quantity': float(total_qty),
            'total_consumption_amount': float(total_amt)
        }
        return JsonResponse(payload)
        
    except Exception as e:
        logger.error(f"Error in get_daily_consumption_summary: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)