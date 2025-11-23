import json
import calendar
import logging
from decimal import Decimal
from datetime import datetime, timedelta, date
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from backend.dynamodb_service import dynamodb_service
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def get_daily_report(request):
    """Get daily report - converted from Lambda get_daily_report function"""
    try:
        body = json.loads(request.body)
        
        rd = body.get("report_date")
        if rd is None:
            rd = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")
        elif not isinstance(rd, str):
            return JsonResponse({"error": "report_date must be a string"}, status=400)
        rd = rd.strip()

        # Get all stock items
        stock_items = dynamodb_service.scan_table('STOCK')
        
        # Get transactions for the date
        transactions = dynamodb_service.scan_table(
            'stock_transactions',
            FilterExpression='#date = :report_date',
            ExpressionAttributeNames={'#date': 'date'},
            ExpressionAttributeValues={':report_date': rd}
        )
        
        # Build transactions section grouped by date with operations
        tx_section = {}
        for txn in transactions:
            txn_date = txn.get('date', '')
            if txn_date not in tx_section:
                tx_section[txn_date] = {'operations': []}
            
            # Convert Decimal objects to float in details
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
        
        # Get all groups for group mapping
        groups = dynamodb_service.scan_table('GROUPS')
        group_dict = {g['group_id']: g for g in groups}
        
        def get_group_chain(group_id):
            """Walk up the Groups table to build [parent, …, child] chain of names."""
            chain = []
            while group_id:
                grp = group_dict.get(group_id)
                if not grp:
                    break
                chain.insert(0, grp['name'])
                group_id = grp.get('parent_id')
            return chain
        
        # Build per-item rows with opening, inward, consumption, balance
        items = []
        for item in stock_items:
            item_id = item.get('item_id', '')
            rate = float(item.get('cost_per_unit', 0))
            current_qty = int(item.get('quantity', 0))
            
            # For simplicity, use current stock as opening (in real implementation, 
            # you'd fetch from SaveOpeningStock transaction)
            opening_qty = current_qty
            opening_amount = opening_qty * rate
            
            # Calculate inward from AddStockQuantity transactions
            inward_qty = 0
            for txn in transactions:
                if (txn.get('operation_type') == 'AddStockQuantity' and 
                    txn.get('details', {}).get('item_id') == item_id):
                    inward_qty += int(txn.get('details', {}).get('quantity_added', 0))
            inward_amount = inward_qty * rate
            
            # Calculate consumption from AddDefectiveGoods and PushToProduction
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
            
            # Calculate balance
            balance_qty = opening_qty + inward_qty - consumption_qty
            balance_amount = balance_qty * rate
            
            # Get group information
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
        logger.error(f"Error in get_daily_report: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_weekly_report(request):
    """Get weekly report - converted from Lambda get_weekly_report function"""
    try:
        body = json.loads(request.body)
        
        now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        end_date = body.get("end_date", now.strftime("%Y-%m-%d")).strip()
        start_date = body.get("start_date", (now - timedelta(days=7)).strftime("%Y-%m-%d")).strip()
        
        logger.info(f"Generating weekly report from {start_date} to {end_date}")

        # Get all stock items
        stock_items = dynamodb_service.scan_table('STOCK')
        
        # Get transactions for the date range
        transactions = dynamodb_service.scan_table(
            'stock_transactions',
            FilterExpression='#date BETWEEN :start_date AND :end_date',
            ExpressionAttributeNames={'#date': 'date'},
            ExpressionAttributeValues={
                ':start_date': start_date,
                ':end_date': end_date
            }
        )
        
        # Get all groups for group mapping
        groups = dynamodb_service.scan_table('GROUPS')
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
        
        # Build per-item rows with calculations for the week
        items = []
        for item in stock_items:
            item_id = item.get('item_id', '')
            rate = float(item.get('cost_per_unit', 0))
            current_qty = int(item.get('quantity', 0))
            
            # Use current stock as opening
            opening_qty = current_qty
            opening_amount = opening_qty * rate
            
            # Calculate inward from AddStockQuantity transactions
            inward_qty = 0
            for txn in transactions:
                if (txn.get('operation_type') == 'AddStockQuantity' and 
                    txn.get('details', {}).get('item_id') == item_id):
                    inward_qty += int(txn.get('details', {}).get('quantity_added', 0))
            inward_amount = inward_qty * rate
            
            # Calculate consumption from AddDefectiveGoods and PushToProduction
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
            
            # Calculate balance
            balance_qty = opening_qty + inward_qty - consumption_qty
            balance_amount = balance_qty * rate
            
            # Get group information
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
        
        # Build transactions section grouped by date
        tx_section = {}
        for txn in transactions:
            txn_date = txn.get('date', '')
            if txn_date not in tx_section:
                tx_section[txn_date] = {'operations': []}
            
            # Convert Decimal objects to float in details
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
            "report_period": {"start_date": start_date, "end_date": end_date},
            "items": items,
            "transactions": tx_section,
            "group_summary": group_summary_list
        }

        return JsonResponse(payload)
        
    except Exception as e:
        logger.error(f"Error in get_weekly_report: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_monthly_report(request):
    """Get monthly report - converted from Lambda get_monthly_report function"""
    try:
        body = json.loads(request.body)
        
        month = body.get("month")
        if not isinstance(month, str):
            return JsonResponse({"error": "'month' must be a string in YYYY-MM"}, status=400)
        
        month = month.strip()
        try:
            year, mon = map(int, month.split("-"))
        except ValueError:
            return JsonResponse({"error": "'month' must be in YYYY-MM"}, status=400)

        # Compute first/last day of month
        first = date(year, mon, 1)
        last = date(year, mon, calendar.monthrange(year, mon)[1])
        start_date = first.strftime("%Y-%m-%d")
        end_date = last.strftime("%Y-%m-%d")
        
        logger.info(f"Generating monthly report for {month} ({start_date} to {end_date})")

        # Get all stock items
        stock_items = dynamodb_service.scan_table('STOCK')
        
        # Get all groups
        groups = dynamodb_service.scan_table('GROUPS')
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
        
        # Get transactions for the month
        transactions = dynamodb_service.scan_table(
            'stock_transactions',
            FilterExpression='#date BETWEEN :start_date AND :end_date',
            ExpressionAttributeNames={'#date': 'date'},
            ExpressionAttributeValues={
                ':start_date': start_date,
                ':end_date': end_date
            }
        )
        
        # Build per-item rows with calculations for the month
        items = []
        for item in stock_items:
            item_id = item.get('item_id', '')
            rate = float(item.get('cost_per_unit', 0))
            current_qty = int(item.get('quantity', 0))
            
            # Use current stock as opening
            opening_qty = current_qty
            opening_amount = opening_qty * rate
            
            # Calculate inward from AddStockQuantity transactions
            inward_qty = 0
            for txn in transactions:
                if (txn.get('operation_type') == 'AddStockQuantity' and 
                    txn.get('details', {}).get('item_id') == item_id):
                    inward_qty += int(txn.get('details', {}).get('quantity_added', 0))
            inward_amount = inward_qty * rate
            
            # Calculate consumption from AddDefectiveGoods and PushToProduction
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
            
            # Calculate balance
            balance_qty = opening_qty + inward_qty - consumption_qty
            balance_amount = balance_qty * rate
            
            # Get group information
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
            "report_period": {"start_date": start_date, "end_date": end_date},
            "month": month,
            "items": items,
            "group_summary": group_summary_list
        }

        return JsonResponse(payload)
        
    except Exception as e:
        logger.error(f"Error in get_monthly_report: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_monthly_production_summary(request):
    """Get monthly production summary - converted from Lambda get_monthly_production_summary function"""
    try:
        body = json.loads(request.body)
        
        # Get current month in IST if no dates provided
        now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        from_date = body.get('from_date', now.strftime("%Y-%m-01"))
        to_date = body.get('to_date', now.strftime("%Y-%m-%d"))
        
        # Use Django ORM to get production records
        try:
            from production.models import PushToProduction
            
            # Convert date strings to datetime objects for filtering
            start_datetime = datetime.strptime(from_date, '%Y-%m-%d')
            end_datetime = datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            
            # Query PushToProduction records within date range
            productions = PushToProduction.objects.filter(
                timestamp__gte=start_datetime,
                timestamp__lte=end_datetime
            )
            
            # Group by product for summary
            summary_dict = {}
            total_quantity = 0
            
            for prod in productions:
                product_id = prod.product_id
                product_name = prod.product_name
                quantity = int(prod.quantity_produced)
                
                if product_id not in summary_dict:
                    summary_dict[product_id] = {
                        'product_id': product_id,
                        'product_name': product_name,
                        'total_quantity': 0
                    }
                
                summary_dict[product_id]['total_quantity'] += quantity
                total_quantity += quantity
            
            payload = {
                "from_date": from_date,
                "to_date": to_date,
                "items": list(summary_dict.values()),
                "total": total_quantity
            }
            
        except Exception as e:
            logger.error(f"DynamoDB error: {e}")
            payload = {
                "from_date": from_date,
                "to_date": to_date,
                "items": [],
                "total": 0
            }
        
        return JsonResponse(payload)
        
    except Exception as e:
        logger.error(f"Error in get_monthly_production_summary: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_daily_push_to_production(request):
    """Get daily production push report - converted from Lambda get_daily_push_to_production function"""
    try:
        body = json.loads(request.body)
        
        username = body.get('username', 'Unknown')
        date_str = body.get('date')
        if not date_str:
            return JsonResponse({"error": "'date' is required (format: YYYY-MM-DD)"}, status=400)

        # Try different table names that might exist
        table_names = ['PUSH_TO_PRODUCTION', 'push_to_production', 'PRODUCTION', 'production']
        all_productions = []
        
        for table_name in table_names:
            try:
                productions = dynamodb_service.scan_table(table_name)
                if productions:
                    all_productions = productions
                    logger.info(f"Found {len(productions)} records in table: {table_name}")
                    break
            except Exception as e:
                logger.info(f"Table {table_name} not found or error: {e}")
        
        logger.info(f"Total production records found: {len(all_productions)}")
        
        # Debug: log first few records to see structure
        if all_productions:
            logger.info(f"Sample record: {all_productions[0]}")
        
        # Filter records where timestamp starts with the date
        productions = []
        for prod in all_productions:
            timestamp = prod.get('timestamp', '')
            logger.info(f"Checking timestamp: {timestamp} against date: {date_str}")
            if timestamp.startswith(date_str):
                productions.append(prod)
        
        logger.info(f"Filtered production records: {len(productions)}")
        
        # Group by product for summary
        from collections import defaultdict
        summary_dict = defaultdict(lambda: {
            'product_id': '',
            'product_name': '',
            'total_quantity': 0
        })
        items = []
        
        for prod in productions:
            product_id = prod.get('product_id', '')
            product_name = prod.get('product_name', '')
            quantity = int(prod.get('quantity_produced', 0))
            
            # Add to summary
            summary_dict[product_id]['product_id'] = product_id
            summary_dict[product_id]['product_name'] = product_name
            summary_dict[product_id]['total_quantity'] += quantity
            
            # Add to items
            items.append({
                'push_id': prod.get('push_id', ''),
                'product_id': product_id,
                'product_name': product_name,
                'quantity': quantity,
                'timestamp': prod.get('timestamp', ''),
                'username': prod.get('username', '')
            })
        
        result = {
            "summary": list(summary_dict.values()),
            "items": items
        }

        logger.info(f"User '{username}' retrieved daily push-to-production records for {date_str}")
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in get_daily_push_to_production: {e}")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_weekly_push_to_production(request):
    """Get weekly production push report - converted from Lambda get_weekly_push_to_production function"""
    try:
        import boto3
        
        body = json.loads(request.body)
        
        username = body.get('username', 'Unknown')
        from_str = body.get('from_date')
        to_str = body.get('to_date')
        if not from_str or not to_str:
            return JsonResponse({
                "error": "'from_date' and 'to_date' are required (format: YYYY-MM-DD)"
            }, status=400)

        try:
            # Direct boto3 connection like Lambda
            dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            table = dynamodb.Table('push_to_production')
            
            # Scan for production records in date range
            response = table.scan(
                FilterExpression='#date BETWEEN :from_date AND :to_date',
                ExpressionAttributeNames={'#date': 'date'},
                ExpressionAttributeValues={
                    ':from_date': from_str,
                    ':to_date': to_str
                }
            )
            productions = response.get('Items', [])
            
            # Group by product for summary
            summary_dict = {}
            items = []
            
            for prod in productions:
                product_id = prod.get('product_id', '')
                product_name = prod.get('product_name', '')
                quantity = int(prod.get('quantity', 0))
                
                # Add to summary
                if product_id not in summary_dict:
                    summary_dict[product_id] = {
                        'product_id': product_id,
                        'product_name': product_name,
                        'total_quantity': 0
                    }
                summary_dict[product_id]['total_quantity'] += quantity
                
                # Add to items
                items.append({
                    'push_id': prod.get('push_id', ''),
                    'product_id': product_id,
                    'product_name': product_name,
                    'quantity': quantity,
                    'date': prod.get('date', ''),
                    'timestamp': prod.get('timestamp', ''),
                    'username': prod.get('username', '')
                })
            
            result = {
                "summary": list(summary_dict.values()),
                "items": items
            }
            
        except Exception as e:
            logger.error(f"DynamoDB error: {e}")
            result = {"summary": [], "items": []}

        logger.info(f"User '{username}' retrieved weekly push-to-production records from {from_str} to {to_str}")
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in get_weekly_push_to_production: {e}")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_monthly_push_to_production(request):
    """Get monthly production push report - converted from Lambda get_monthly_push_to_production function"""
    try:
        import boto3
        
        body = json.loads(request.body)
        
        username = body.get('username', 'Unknown')
        from_str = body.get('from_date')
        to_str = body.get('to_date')
        if not from_str or not to_str:
            return JsonResponse({
                "error": "'from_date' and 'to_date' are required (format: YYYY-MM-DD)"
            }, status=400)

        try:
            # Direct boto3 connection like Lambda
            dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            table = dynamodb.Table('push_to_production')
            
            # Scan for production records in date range
            response = table.scan(
                FilterExpression='#date BETWEEN :from_date AND :to_date',
                ExpressionAttributeNames={'#date': 'date'},
                ExpressionAttributeValues={
                    ':from_date': from_str,
                    ':to_date': to_str
                }
            )
            productions = response.get('Items', [])
            
            # Group by product for summary
            summary_dict = {}
            items = []
            
            for prod in productions:
                product_id = prod.get('product_id', '')
                product_name = prod.get('product_name', '')
                quantity = int(prod.get('quantity', 0))
                
                # Add to summary
                if product_id not in summary_dict:
                    summary_dict[product_id] = {
                        'product_id': product_id,
                        'product_name': product_name,
                        'total_quantity': 0
                    }
                summary_dict[product_id]['total_quantity'] += quantity
                
                # Add to items
                items.append({
                    'push_id': prod.get('push_id', ''),
                    'product_id': product_id,
                    'product_name': product_name,
                    'quantity': quantity,
                    'date': prod.get('date', ''),
                    'timestamp': prod.get('timestamp', ''),
                    'username': prod.get('username', '')
                })
            
            result = {
                "summary": list(summary_dict.values()),
                "items": items
            }
            
        except Exception as e:
            logger.error(f"DynamoDB error: {e}")
            result = {"summary": [], "items": []}

        logger.info(f"User '{username}' retrieved monthly push-to-production records from {from_str} to {to_str}")
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in get_monthly_push_to_production: {e}")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_daily_consumption_summary(request):
    """Get daily consumption summary - converted from Lambda get_daily_consumption_summary function"""
    try:
        body = json.loads(request.body)
        
        report_date = body.get("report_date")
        if not report_date:
            report_date = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")
        report_date = report_date.strip()

        # Get transactions for the date from DynamoDB
        transactions = dynamodb_service.scan_table(
            'stock_transactions',
            FilterExpression='#date = :report_date',
            ExpressionAttributeNames={'#date': 'date'},
            ExpressionAttributeValues={':report_date': report_date}
        )
        
        # Extract consumption details (AddDefectiveGoods & PushToProduction)
        consumption_details = []
        for tx in transactions:
            op = tx.get("operation_type", "")
            if op in ["AddDefectiveGoods", "PushToProduction"]:
                d = tx.get("details", {})
                if op == "PushToProduction":
                    for item_id, qty in d.get("deductions", {}).items():
                        consumption_details.append({
                            "item_id": item_id,
                            "quantity_consumed": Decimal(str(qty))
                        })
                else:  # AddDefectiveGoods
                    consumption_details.append({
                        "item_id": d.get("item_id", "Unknown"),
                        "quantity_consumed": Decimal(str(d.get("defective_added", 0)))
                    })
        
        # Summarize consumption by item_id
        from collections import defaultdict
        summary_map = defaultdict(Decimal)
        for d in consumption_details:
            summary_map[d['item_id']] += d['quantity_consumed']
        
        # Get stock items and groups
        stock_items = dynamodb_service.scan_table('STOCK')
        stock_dict = {item['item_id']: item for item in stock_items}
        groups = dynamodb_service.scan_table('GROUPS')
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
        
        # Build flat list with group info
        flat = []
        for item_id, qty in summary_map.items():
            if item_id in stock_dict:
                stock_item = stock_dict[item_id]
                group_id = stock_item.get('group_id')
                chain = get_group_chain(group_id) if group_id else []
                
                flat.append({
                    "item_id": item_id,
                    "group": chain[0] if len(chain) >= 1 else "Unknown",
                    "subgroup": chain[1] if len(chain) >= 2 else "Unknown",
                    "total_quantity_consumed": float(qty),
                    "cost_per_unit": float(stock_item.get('cost_per_unit', 0)),
                    "current_quantity": int(stock_item.get('quantity', 0)),
                    "defective": int(stock_item.get('defective', 0)),
                    "total_quantity": int(stock_item.get('total_quantity', 0))
                })
        
        # Build nested structure
        nested = {}
        for e in flat:
            g = e['group']
            s = e['subgroup']
            if g not in nested:
                nested[g] = {}
            if s not in nested[g]:
                nested[g][s] = []
            
            # Calculate balance (current stock - consumed)
            balance_qty = e['current_quantity'] - e['total_quantity_consumed']
            
            nested[g][s].append({
                "item_id": e["item_id"],
                "total_quantity_consumed": e["total_quantity_consumed"],
                "current_stock": e['current_quantity'],
                "balance_after_consumption": balance_qty
            })
        
        # Calculate totals
        total_qty = sum(summary_map.values())
        total_amt = Decimal('0')
        
        for item_id, qty in summary_map.items():
            if item_id in stock_dict:
                rate = Decimal(str(stock_dict[item_id].get('cost_per_unit', 0)))
                total_amt += rate * qty
        
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

@csrf_exempt
@require_http_methods(["POST"])
def get_weekly_consumption_summary(request):
    """Get weekly consumption summary - converted from Lambda get_weekly_consumption_summary function"""
    try:
        body = json.loads(request.body)
        
        now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        end_date = body.get("end_date", now.strftime("%Y-%m-%d")).strip()
        start_date = body.get("start_date", (now - timedelta(days=7)).strftime("%Y-%m-%d")).strip()

        # Get transactions for the date range from DynamoDB
        transactions = dynamodb_service.scan_table(
            'stock_transactions',
            FilterExpression='#date BETWEEN :start_date AND :end_date',
            ExpressionAttributeNames={'#date': 'date'},
            ExpressionAttributeValues={
                ':start_date': start_date,
                ':end_date': end_date
            }
        )
        
        # Get stock items and groups
        stock_items = dynamodb_service.scan_table('STOCK')
        stock_dict = {item['item_id']: item for item in stock_items}
        groups = dynamodb_service.scan_table('GROUPS')
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
        
        # Group consumption by date
        date_summary = {}
        total_consumption_quantity = 0
        total_consumption_amount = 0.0
        
        # Initialize all dates in range
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        while current_date <= end_dt:
            date_summary[current_date.strftime('%Y-%m-%d')] = {}
            current_date += timedelta(days=1)
        
        # Process ALL transactions by date - ensure we capture every single transaction
        for tx in transactions:
            op = tx.get("operation_type", "")
            if op in ["AddDefectiveGoods", "PushToProduction"]:
                tx_date = tx.get('date', '')
                d = tx.get("details", {})
                
                if op == "PushToProduction":
                    # Process each deduction in the transaction
                    deductions = d.get("deductions", {})
                    for item_id, qty in deductions.items():
                        # Get group info for item
                        group = "Unknown"
                        subgroup = "Unknown"
                        cost_per_unit = 0
                        
                        if item_id in stock_dict:
                            stock_item = stock_dict[item_id]
                            group_id = stock_item.get('group_id')
                            chain = get_group_chain(group_id) if group_id else []
                            group = chain[0] if len(chain) >= 1 else "Unknown"
                            subgroup = chain[1] if len(chain) >= 2 else "Unknown"
                            cost_per_unit = float(stock_item.get('cost_per_unit', 0))
                        
                        # Ensure date exists
                        if tx_date not in date_summary:
                            date_summary[tx_date] = {}
                        if group not in date_summary[tx_date]:
                            date_summary[tx_date][group] = {}
                        if subgroup not in date_summary[tx_date][group]:
                            date_summary[tx_date][group][subgroup] = []
                        
                        # Add this specific transaction (don't aggregate, add each occurrence)
                        date_summary[tx_date][group][subgroup].append({
                            "item_id": item_id,
                            "quantity": float(qty)
                        })
                        
                        total_consumption_quantity += float(qty)
                        total_consumption_amount += float(qty) * cost_per_unit
                
                elif op == "AddDefectiveGoods":
                    # Process defective goods transaction
                    item_id = d.get("item_id", "Unknown")
                    qty = d.get("defective_added", 0)
                    
                    if qty > 0:  # Only process if there's actual quantity
                        # Get group info for item
                        group = "Unknown"
                        subgroup = "Unknown"
                        cost_per_unit = 0
                        
                        if item_id in stock_dict:
                            stock_item = stock_dict[item_id]
                            group_id = stock_item.get('group_id')
                            chain = get_group_chain(group_id) if group_id else []
                            group = chain[0] if len(chain) >= 1 else "Unknown"
                            subgroup = chain[1] if len(chain) >= 2 else "Unknown"
                            cost_per_unit = float(stock_item.get('cost_per_unit', 0))
                        
                        # Ensure date exists
                        if tx_date not in date_summary:
                            date_summary[tx_date] = {}
                        if group not in date_summary[tx_date]:
                            date_summary[tx_date][group] = {}
                        if subgroup not in date_summary[tx_date][group]:
                            date_summary[tx_date][group][subgroup] = []
                        
                        # Add this specific transaction
                        date_summary[tx_date][group][subgroup].append({
                            "item_id": item_id,
                            "quantity": float(qty)
                        })
                        
                        total_consumption_quantity += float(qty)
                        total_consumption_amount += float(qty) * cost_per_unit
        
        payload = {
            "report_date": end_date,
            "consumption_summary": date_summary,
            "total_consumption_quantity": total_consumption_quantity,
            "total_consumption_amount": total_consumption_amount
        }
        
        return JsonResponse(payload)
        
    except Exception as e:
        logger.error(f"Error in get_weekly_consumption_summary: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_monthly_consumption_summary(request):
    """Get monthly consumption summary - converted from Lambda get_monthly_consumption_summary function"""
    try:
        body = json.loads(request.body)
        
        month_str = body.get("month")
        if not month_str:
            now = datetime.utcnow() + timedelta(hours=5, minutes=30)
            month_str = now.strftime("%Y-%m")
        
        try:
            year, month = map(int, month_str.split("-"))
        except ValueError:
            return JsonResponse({"error": "'month' must be in YYYY-MM format"}, status=400)
        
        # Calculate month date range
        import calendar
        start_date = f"{year}-{month:02d}-01"
        last_day = calendar.monthrange(year, month)[1]
        end_date = f"{year}-{month:02d}-{last_day:02d}"

        try:
            # Get transactions for the month from DynamoDB - using correct table name
            transactions = dynamodb_service.scan_table(
                'stock_transactions',
                FilterExpression='#date BETWEEN :start_date AND :end_date',
                ExpressionAttributeNames={'#date': 'date'},
                ExpressionAttributeValues={
                    ':start_date': start_date,
                    ':end_date': end_date
                }
            )
            
            # Extract consumption details (AddDefectiveGoods & PushToProduction)
            consumption_details = []
            for tx in transactions:
                op = tx.get("operation_type", "")
                if op in ["AddDefectiveGoods", "PushToProduction"]:
                    d = tx.get("details", {})
                    if op == "PushToProduction":
                        for item_id, qty in d.get("deductions", {}).items():
                            consumption_details.append({
                                "item_id": item_id,
                                "quantity_consumed": qty,
                                "operation": op,
                                "timestamp": tx.get("timestamp", "")
                            })
                    else:  # AddDefectiveGoods
                        qty = d.get("defective_added", 0)
                        consumption_details.append({
                            "item_id": d.get("item_id", "Unknown"),
                            "quantity_consumed": qty,
                            "operation": op,
                            "timestamp": tx.get("timestamp", "")
                        })
            
            # Summarize consumption details by item_id
            from collections import defaultdict
            summary_map = defaultdict(Decimal)
            for d in consumption_details:
                summary_map[d['item_id']] += Decimal(str(d['quantity_consumed']))
            
            # Get stock items for cost calculation
            stock_items = dynamodb_service.scan_table('STOCK')
            stock_dict = {item['item_id']: item for item in stock_items}
            
            # Build nested consumption summary by group and subgroup
            groups = dynamodb_service.scan_table('GROUPS')
            group_dict = {g['group_id']: g for g in groups}
            
            def get_group_chain(group_id):
                """Walk up the Groups table to build [parent, …, child] chain of names."""
                chain = []
                while group_id:
                    grp = group_dict.get(group_id)
                    if not grp:
                        break
                    chain.insert(0, grp['name'])
                    group_id = grp.get('parent_id')
                return chain
            
            nested_summary = {}
            total_consumption_quantity = 0
            total_consumption_amount = 0.0
            
            for item_id, qty in summary_map.items():
                if item_id in stock_dict:
                    stock_item = stock_dict[item_id]
                    group_id = stock_item.get('group_id')
                    
                    # Build group chain
                    chain = get_group_chain(group_id) if group_id else []
                    group = chain[0] if len(chain) >= 1 else "Unknown"
                    subgroup = chain[1] if len(chain) >= 2 else "Unknown"
                    
                    # Calculate cost
                    cost_per_unit = float(stock_item.get('cost_per_unit', 0))
                    amount = float(qty) * cost_per_unit
                    
                    # Add to nested structure
                    if group not in nested_summary:
                        nested_summary[group] = {}
                    if subgroup not in nested_summary[group]:
                        nested_summary[group][subgroup] = []
                    
                    nested_summary[group][subgroup].append({
                        "item_id": item_id,
                        "total_quantity_consumed": float(qty)
                    })
                    
                    total_consumption_quantity += float(qty)
                    total_consumption_amount += amount
            
            payload = {
                "month": month_str,
                "start_date": start_date,
                "end_date": end_date,
                "consumption_summary": nested_summary,
                "total_consumption_quantity": total_consumption_quantity,
                "total_consumption_amount": total_consumption_amount
            }
            
        except Exception as e:
            logger.error(f"Error fetching consumption data: {e}")
            payload = {
                "month": month_str,
                "start_date": start_date,
                "end_date": end_date,
                "consumption_summary": {},
                "total_consumption_quantity": 0,
                "total_consumption_amount": 0.0
            }
        
        return JsonResponse(payload)
        
    except Exception as e:
        logger.error(f"Error in get_monthly_consumption_summary: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_daily_inward(request):
    """Get daily inward report - converted from Lambda get_daily_inward function"""
    try:
        body = json.loads(request.body)
        
        report_date = body.get("report_date")
        if report_date is None:
            report_date = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")
        report_date = report_date.strip()

        try:
            # Get transactions for the date from DynamoDB - using correct table name
            transactions = dynamodb_service.scan_table(
                'stock_transactions',
                FilterExpression='#date = :report_date',
                ExpressionAttributeNames={'#date': 'date'},
                ExpressionAttributeValues={':report_date': report_date}
            )
            
            # Extract inward details (AddStockQuantity operations)
            inward_details = []
            for tx in transactions:
                op = tx.get("operation_type", "")
                if op == "AddStockQuantity":
                    d = tx.get("details", {})
                    inward_details.append({
                        "item_id": d.get("item_id", "Unknown"),
                        "quantity_added": float(d.get("quantity_added", 0)),
                        "added_cost": float(d.get("added_cost", 0)),
                        "timestamp": tx.get("timestamp", ""),
                        "username": d.get("username", "")
                    })
            
            # Get stock items for additional info
            stock_items = dynamodb_service.scan_table('STOCK')
            stock_dict = {item['item_id']: item for item in stock_items}
            
            # Build inward summary by group
            groups = dynamodb_service.scan_table('GROUPS')
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
            
            inward_summary = {}
            total_inward_quantity = 0
            total_inward_amount = 0.0
            
            for detail in inward_details:
                item_id = detail['item_id']
                qty = detail['quantity_added']
                cost = detail['added_cost']
                
                if item_id in stock_dict:
                    stock_item = stock_dict[item_id]
                    group_id = stock_item.get('group_id')
                    
                    # Build group chain
                    chain = get_group_chain(group_id) if group_id else []
                    group = chain[0] if len(chain) >= 1 else "Unknown"
                    subgroup = chain[1] if len(chain) >= 2 else "Unknown"
                    
                    # Add to nested structure
                    if group not in inward_summary:
                        inward_summary[group] = {}
                    if subgroup not in inward_summary[group]:
                        inward_summary[group][subgroup] = []
                    
                    inward_summary[group][subgroup].append({
                        "item_id": item_id,
                        "item_name": stock_item.get('name', ''),
                        "quantity_added": qty,
                        "added_cost": cost,
                        "timestamp": detail['timestamp'],
                        "username": detail['username']
                    })
                    
                    total_inward_quantity += qty
                    total_inward_amount += cost
            
            payload = {
                "report_period": {"start_date": report_date, "end_date": report_date},
                "report_date": report_date,
                "inward_summary": inward_summary,
                "total_inward_quantity": total_inward_quantity,
                "total_inward_amount": total_inward_amount
            }
            
        except Exception as e:
            logger.error(f"Error fetching inward data: {e}")
            payload = {
                "report_period": {"start_date": report_date, "end_date": report_date},
                "report_date": report_date,
                "inward_summary": {},
                "total_inward_quantity": 0,
                "total_inward_amount": 0.0
            }
        
        return JsonResponse(payload)
        
    except Exception as e:
        logger.error(f"Error in get_daily_inward: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_weekly_inward(request):
    """Get weekly inward report - converted from Lambda get_weekly_inward function"""
    try:
        body = json.loads(request.body)
        
        now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        end_date = body.get("end_date", now.strftime("%Y-%m-%d")).strip()
        start_date = body.get("start_date", (now - timedelta(days=7)).strftime("%Y-%m-%d")).strip()

        try:
            # Get transactions for the date range from DynamoDB - using correct table name
            transactions = dynamodb_service.scan_table(
                'stock_transactions',
                FilterExpression='#date BETWEEN :start_date AND :end_date',
                ExpressionAttributeNames={'#date': 'date'},
                ExpressionAttributeValues={
                    ':start_date': start_date,
                    ':end_date': end_date
                }
            )
            
            # Extract inward details (AddStockQuantity operations)
            inward_details = []
            for tx in transactions:
                op = tx.get("operation_type", "")
                if op == "AddStockQuantity":
                    d = tx.get("details", {})
                    inward_details.append({
                        "item_id": d.get("item_id", "Unknown"),
                        "quantity_added": float(d.get("quantity_added", 0)),
                        "added_cost": float(d.get("added_cost", 0)),
                        "timestamp": tx.get("timestamp", ""),
                        "username": d.get("username", ""),
                        "date": tx.get("date", "")
                    })
            
            # Get stock items for additional info
            stock_items = dynamodb_service.scan_table('STOCK')
            stock_dict = {item['item_id']: item for item in stock_items}
            
            # Build inward summary by group
            groups = dynamodb_service.scan_table('GROUPS')
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
            
            inward_summary = {}
            total_inward_quantity = 0
            total_inward_amount = 0.0
            
            for detail in inward_details:
                item_id = detail['item_id']
                qty = detail['quantity_added']
                cost = detail['added_cost']
                
                if item_id in stock_dict:
                    stock_item = stock_dict[item_id]
                    group_id = stock_item.get('group_id')
                    
                    # Build group chain
                    chain = get_group_chain(group_id) if group_id else []
                    group = chain[0] if len(chain) >= 1 else "Unknown"
                    subgroup = chain[1] if len(chain) >= 2 else "Unknown"
                    
                    # Add to nested structure
                    if group not in inward_summary:
                        inward_summary[group] = {}
                    if subgroup not in inward_summary[group]:
                        inward_summary[group][subgroup] = []
                    
                    inward_summary[group][subgroup].append({
                        "item_id": item_id,
                        "item_name": stock_item.get('name', ''),
                        "quantity_added": qty,
                        "added_cost": cost,
                        "date": detail['date'],
                        "timestamp": detail['timestamp'],
                        "username": detail['username']
                    })
                    
                    total_inward_quantity += qty
                    total_inward_amount += cost
            
            payload = {
                "report_period": {"start_date": start_date, "end_date": end_date},
                "start_date": start_date,
                "end_date": end_date,
                "inward_summary": inward_summary,
                "total_inward_quantity": total_inward_quantity,
                "total_inward_amount": total_inward_amount
            }
            
        except Exception as e:
            logger.error(f"Error fetching inward data: {e}")
            payload = {
                "report_period": {"start_date": start_date, "end_date": end_date},
                "start_date": start_date,
                "end_date": end_date,
                "inward_summary": {},
                "total_inward_quantity": 0,
                "total_inward_amount": 0.0
            }
        
        return JsonResponse(payload)
        
    except Exception as e:
        logger.error(f"Error in get_weekly_inward: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_monthly_inward(request):
    """Get monthly inward report - converted from Lambda get_monthly_inward function"""
    try:
        body = json.loads(request.body)
        
        month_str = body.get("month")
        if not month_str:
            now = datetime.utcnow() + timedelta(hours=5, minutes=30)
            month_str = now.strftime("%Y-%m")
        
        try:
            year, month = map(int, month_str.split("-"))
        except ValueError:
            return JsonResponse({"error": "'month' must be in YYYY-MM format"}, status=400)
        
        # Calculate month date range
        import calendar
        start_date = f"{year}-{month:02d}-01"
        last_day = calendar.monthrange(year, month)[1]
        end_date = f"{year}-{month:02d}-{last_day:02d}"

        try:
            # Get transactions for the month from DynamoDB - using correct table name
            transactions = dynamodb_service.scan_table(
                'stock_transactions',
                FilterExpression='#date BETWEEN :start_date AND :end_date',
                ExpressionAttributeNames={'#date': 'date'},
                ExpressionAttributeValues={
                    ':start_date': start_date,
                    ':end_date': end_date
                }
            )
            
            # Extract inward details (AddStockQuantity operations)
            inward_details = []
            for tx in transactions:
                op = tx.get("operation_type", "")
                if op == "AddStockQuantity":
                    d = tx.get("details", {})
                    inward_details.append({
                        "item_id": d.get("item_id", "Unknown"),
                        "quantity_added": float(d.get("quantity_added", 0)),
                        "added_cost": float(d.get("added_cost", 0)),
                        "timestamp": tx.get("timestamp", ""),
                        "username": d.get("username", ""),
                        "date": tx.get("date", "")
                    })
            
            # Get stock items for additional info
            stock_items = dynamodb_service.scan_table('STOCK')
            stock_dict = {item['item_id']: item for item in stock_items}
            
            # Build inward summary by group
            groups = dynamodb_service.scan_table('GROUPS')
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
            
            inward_summary = {}
            total_inward_quantity = 0
            total_inward_amount = 0.0
            
            for detail in inward_details:
                item_id = detail['item_id']
                qty = detail['quantity_added']
                cost = detail['added_cost']
                
                if item_id in stock_dict:
                    stock_item = stock_dict[item_id]
                    group_id = stock_item.get('group_id')
                    
                    # Build group chain
                    chain = get_group_chain(group_id) if group_id else []
                    group = chain[0] if len(chain) >= 1 else "Unknown"
                    subgroup = chain[1] if len(chain) >= 2 else "Unknown"
                    
                    # Add to nested structure
                    if group not in inward_summary:
                        inward_summary[group] = {}
                    if subgroup not in inward_summary[group]:
                        inward_summary[group][subgroup] = []
                    
                    inward_summary[group][subgroup].append({
                        "item_id": item_id,
                        "item_name": stock_item.get('name', ''),
                        "quantity_added": qty,
                        "added_cost": cost,
                        "date": detail['date'],
                        "timestamp": detail['timestamp'],
                        "username": detail['username']
                    })
                    
                    total_inward_quantity += qty
                    total_inward_amount += cost
            
            payload = {
                "report_period": {"start_date": start_date, "end_date": end_date},
                "month": month_str,
                "start_date": start_date,
                "end_date": end_date,
                "inward_summary": inward_summary,
                "total_inward_quantity": total_inward_quantity,
                "total_inward_amount": total_inward_amount
            }
            
        except Exception as e:
            logger.error(f"Error fetching inward data: {e}")
            payload = {
                "report_period": {"start_date": start_date, "end_date": end_date},
                "month": month_str,
                "start_date": start_date,
                "end_date": end_date,
                "inward_summary": {},
                "total_inward_quantity": 0,
                "total_inward_amount": 0.0
            }
        
        return JsonResponse(payload)
        
    except Exception as e:
        logger.error(f"Error in get_monthly_inward: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

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
        production_records = dynamodb_service.scan_table('PUSH_TO_PRODUCTION')
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