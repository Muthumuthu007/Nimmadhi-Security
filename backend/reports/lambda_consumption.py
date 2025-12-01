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

# EXACT Lambda function converted to Django
@csrf_exempt
@require_http_methods(["POST"])
def get_daily_consumption_summary(request):
    """EXACT Lambda get_daily_consumption_summary converted to Django"""
    try:
        body = json.loads(request.body)

        # 1) Determine report_date (IST) - EXACT Lambda logic
        report_date = body.get("report_date")
        if not report_date:
            report_date = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")
        report_date = report_date.strip()

        # 2) Load all transactions on that date - EXACT Lambda logic
        dynamodb = boto3.resource('dynamodb', region_name=settings.AWS_REGION)
        tx_tbl = dynamodb.Table('stock_transactions')
        tx_resp = tx_tbl.scan(FilterExpression=Attr('date').eq(report_date))
        txns = tx_resp.get("Items", [])
        while "LastEvaluatedKey" in tx_resp:
            tx_resp = tx_tbl.scan(
                FilterExpression=Attr('date').eq(report_date),
                ExclusiveStartKey=tx_resp["LastEvaluatedKey"]
            )
            txns.extend(tx_resp.get("Items", []))

        # 3) Extract only consumption operations - EXACT Lambda logic
        def extract_consumption_details(transactions):
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
                                "quantity_consumed": Decimal(str(qty))
                            })
                    else:  # AddDefectiveGoods
                        details.append({
                            "item_id": d.get("item_id", "Unknown"),
                            "quantity_consumed": Decimal(str(d.get("defective_added", 0)))
                        })
            return details
        
        consumption_details = extract_consumption_details(txns)

        # 4) Summarize per‐item quantities - EXACT Lambda logic
        summary_map = defaultdict(Decimal)
        for d in consumption_details:
            summary_map[d['item_id']] += Decimal(str(d['quantity_consumed']))

        # 5) Enrich each item with its group & subgroup - EXACT Lambda logic
        def get_group_chain(group_id):
            """Walk up the Groups table to build [parent, …, child] chain of names."""
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
        
        stock_tbl = dynamodb.Table('stock')
        flat = []
        for item_id, qty in summary_map.items():
            # look up group_id - EXACT Lambda logic
            stock_resp = stock_tbl.get_item(Key={'item_id': item_id})
            group_id = stock_resp.get('Item', {}).get('group_id') if 'Item' in stock_resp else None

            # build full chain: [top_group, sub_group, ...] - EXACT Lambda logic
            chain = get_group_chain(group_id) if group_id else []
            group = chain[0] if len(chain) >= 1 else None
            subgroup = chain[1] if len(chain) >= 2 else None

            flat.append({
                "item_id": item_id,
                "group": group,
                "subgroup": subgroup,
                "total_quantity_consumed": float(qty)
            })

        # 6) Nest into { group → { subgroup → [items…] } } - EXACT Lambda logic
        nested = {}
        for e in flat:
            g = e['group'] or "Unknown"
            s = e['subgroup'] or "Unknown"
            nested.setdefault(g, {}).setdefault(s, []).append({
                "item_id": e["item_id"],
                "total_quantity_consumed": e["total_quantity_consumed"]
            })

        # 7) Compute grand totals - EXACT Lambda logic
        total_qty = sum(summary_map.values())
        total_amt = Decimal('0')
        for item_id, qty in summary_map.items():
            stock_resp = stock_tbl.get_item(Key={'item_id': item_id})
            if 'Item' in stock_resp:
                rate = Decimal(str(stock_resp['Item'].get('cost_per_unit', 0)))
                total_amt += rate * qty

        # 8) Build and return - EXACT Lambda logic
        payload = {
            "report_date": report_date,
            "consumption_summary": nested,
            "total_consumption_quantity": float(total_qty),
            "total_consumption_amount": float(total_amt)
        }
        return JsonResponse(payload)

    except Exception as e:
        logger.error(f"Error in get_daily_consumption_summary: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)