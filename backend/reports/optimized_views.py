"""
Optimized report views with caching
"""
import json
import calendar
import logging
from decimal import Decimal
from datetime import datetime, timedelta, date
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from reports.cache_service import CacheService
from backend.dynamodb_service import dynamodb_service

logger = logging.getLogger(__name__)

@cache_page(60 * 5)  # Cache for 5 minutes
@csrf_exempt
@require_http_methods(["POST"])
def get_daily_report_optimized(request):
    """Optimized daily report with caching"""
    try:
        body = json.loads(request.body)
        
        rd = body.get("report_date")
        if rd is None:
            rd = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")
        rd = rd.strip()

        # Get cached data
        stock_items = CacheService.get_stock_items()
        transactions = CacheService.get_transactions_by_date(rd)
        groups = CacheService.get_groups()
        
        group_dict = {g['group_id']: g for g in groups}
        
        def get_group_chain(group_id):
            chain = []
            while group_id:
                grp = group_dict.get(group_id)
                if not grp:
                    break
                chain.insert(0, grp['name'])
                group_id = grp.get('parent_id')
            return chain
        
        # Build transactions section
        tx_section = {}
        for txn in transactions:
            txn_date = txn.get('date', '')
            if txn_date not in tx_section:
                tx_section[txn_date] = {'operations': []}
            
            details = txn.get('details', {})
            processed_details = {}
            for key, value in details.items():
                if hasattr(value, '__float__'):
                    processed_details[key] = float(value)
                else:
                    processed_details[key] = value
            
            tx_section[txn_date]['operations'].append({
                'operation_type': txn.get('operation_type', ''),
                'transaction_id': txn.get('transaction_id', ''),
                'date': txn_date,
                'details': processed_details,
                'timestamp': txn.get('timestamp', '')
            })
        
        # Build per-item rows
        items = []
        for item in stock_items:
            item_id = item.get('item_id', '')
            rate = float(item.get('cost_per_unit', 0))
            current_qty = int(item.get('quantity', 0))
            
            opening_qty = current_qty
            opening_amount = opening_qty * rate
            
            # Calculate inward
            inward_qty = 0
            for txn in transactions:
                if (txn.get('operation_type') == 'AddStockQuantity' and 
                    txn.get('details', {}).get('item_id') == item_id):
                    inward_qty += int(txn.get('details', {}).get('quantity_added', 0))
            inward_amount = inward_qty * rate
            
            # Calculate consumption
            consumption_qty = 0
            for txn in transactions:
                details = txn.get('details', {})
                if txn.get('operation_type') == 'AddDefectiveGoods' and details.get('item_id') == item_id:
                    consumption_qty += int(details.get('defective_added', 0))
                elif txn.get('operation_type') == 'PushToProduction':
                    deductions = details.get('deductions', {})
                    if item_id in deductions:
                        consumption_qty += int(deductions[item_id])
            consumption_amount = consumption_qty * rate
            
            balance_qty = opening_qty + inward_qty - consumption_qty
            balance_amount = balance_qty * rate
            
            # Get group info
            group_id = item.get('group_id')
            chain = get_group_chain(group_id) if group_id else []
            group_name = chain[0] if len(chain) >= 1 else "Unknown"
            parent_group_name = chain[1] if len(chain) >= 2 else group_name
            
            items.append({
                "description": item_id,
                "rate": rate,
                "opening_stock_qty": opening_qty,
                "opening_stock_amount": opening_amount,
                "inward_qty": inward_qty,
                "inward_amount": inward_amount,
                "consumption_qty": consumption_qty,
                "consumption_amount": consumption_amount,
                "balance_qty": balance_qty,
                "balance_amount": balance_amount,
                "group_name": group_name,
                "parent_group_name": parent_group_name
            })
        
        # Calculate group summaries
        from collections import defaultdict
        group_summary = defaultdict(lambda: {
            "description": "",
            "opening_stock_qty": 0,
            "opening_stock_amount": 0.0,
            "inward_qty": 0,
            "inward_amount": 0.0,
            "consumption_qty": 0,
            "consumption_amount": 0.0,
            "balance_qty": 0,
            "balance_amount": 0.0
        })
        
        for item in items:
            group = item["parent_group_name"]
            group_summary[group]["description"] = group
            group_summary[group]["opening_stock_qty"] += item["opening_stock_qty"]
            group_summary[group]["opening_stock_amount"] += item["opening_stock_amount"]
            group_summary[group]["inward_qty"] += item["inward_qty"]
            group_summary[group]["inward_amount"] += item["inward_amount"]
            group_summary[group]["consumption_qty"] += item["consumption_qty"]
            group_summary[group]["consumption_amount"] += item["consumption_amount"]
            group_summary[group]["balance_qty"] += item["balance_qty"]
            group_summary[group]["balance_amount"] += item["balance_amount"]
        
        # Add grand total
        total_row = {
            "description": "TOTAL",
            "opening_stock_qty": sum(item["opening_stock_qty"] for item in items),
            "opening_stock_amount": sum(item["opening_stock_amount"] for item in items),
            "inward_qty": sum(item["inward_qty"] for item in items),
            "inward_amount": sum(item["inward_amount"] for item in items),
            "consumption_qty": sum(item["consumption_qty"] for item in items),
            "consumption_amount": sum(item["consumption_amount"] for item in items),
            "balance_qty": sum(item["balance_qty"] for item in items),
            "balance_amount": sum(item["balance_amount"] for item in items)
        }
        
        group_summary_list = list(group_summary.values())
        group_summary_list.append(total_row)
        
        payload = {
            "report_period": {"start_date": rd, "end_date": rd},
            "items": items,
            "transactions": tx_section,
            "group_summary": group_summary_list
        }

        return JsonResponse(payload)
        
    except Exception as e:
        logger.error(f"Error in optimized daily report: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)