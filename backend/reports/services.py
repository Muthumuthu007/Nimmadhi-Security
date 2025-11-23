"""
Reports business logic and utilities
Converted from Lambda report helper functions
"""
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

def format_ist_timestamp(iso_timestamp):
    """Format timestamp to IST - converted from Lambda format_ist_timestamp function"""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00').split('+')[0])
        return dt.strftime('%Y-%m-%d %I:%M:%S %p')
    except Exception as e:
        logger.error(f"Error formatting timestamp {iso_timestamp}: {str(e)}")
        return iso_timestamp

def extract_consumption_details(transactions):
    """Extract consumption details from transactions - converted from Lambda function"""
    consumption_ops = ["AddDefectiveGoods", "PushToProduction"]
    details = []
    
    for tx in transactions:
        op = tx.get("operation_type")
        if op in consumption_ops:
            dt = tx.get("details", {})
            if op == "PushToProduction":
                deductions = dt.get("deductions", {})
                for item_id, qty in deductions.items():
                    details.append({
                        "item_id": item_id,
                        "quantity_consumed": qty,
                        "operation": op,
                        "timestamp": format_ist_timestamp(tx.get("timestamp"))
                    })
            else:  # AddDefectiveGoods
                qty = dt.get("defective_added", 0)
                details.append({
                    "item_id": dt.get("item_id", "Unknown"),
                    "quantity_consumed": qty,
                    "operation": op,
                    "timestamp": format_ist_timestamp(tx.get("timestamp"))
                })
    
    return details

def summarize_consumption_details(details):
    """Group consumption details by item_id - converted from Lambda function"""
    summary = {}
    for d in details:
        item = d.get("item_id", "Unknown")
        qty = Decimal(str(d.get("quantity_consumed", 0)))
        summary[item] = summary.get(item, Decimal('0')) + qty
    
    summarized_list = [
        {"item_id": k, "total_quantity_consumed": float(v)} 
        for k, v in summary.items()
    ]
    return summarized_list

def compute_consumption_amount(transactions):
    """Compute total consumption amount - converted from Lambda function"""
    amount = Decimal('0')
    for tx in transactions:
        if tx.get("operation_type") == "PushToProduction":
            dt = tx.get("details", {})
            amt = Decimal(str(dt.get("total_production_cost", 0)))
            amount += amt
    return amount

def group_transactions_by_operation(transactions):
    """Group transactions by operation type - converted from Lambda function"""
    grouped = {}
    for tx in transactions:
        op = tx.get('operation_type', 'UnknownOperation')
        if op not in grouped:
            grouped[op] = []
        grouped[op].append(tx)
    return grouped

def classify_addition_and_consumption(transactions):
    """Classify transactions into additions and consumption - converted from Lambda function"""
    additions_qty = Decimal('0')
    additions_amount = Decimal('0')
    consumption_qty = Decimal('0')
    consumption_amount = Decimal('0')
    
    for tx in transactions:
        op = tx.get('operation_type', '')
        details = tx.get('details', {})
        
        if op in ["CreateStock", "AddStockQuantity", "SubtractDefectiveGoods"]:
            if op == "CreateStock":
                added_qty = Decimal(str(details.get("quantity", 0)))
                added_cost = Decimal(str(details.get("total_cost", 0)))
                additions_qty += added_qty
                additions_amount += added_cost
            elif op == "AddStockQuantity":
                added_qty = Decimal(str(details.get("quantity_added", 0)))
                added_cost = Decimal(str(details.get("added_cost", 0))) if "added_cost" in details else (added_qty * Decimal(str(details.get("cost_per_unit", 0))))
                additions_qty += added_qty
                additions_amount += added_cost
            elif op == "SubtractDefectiveGoods":
                def_sub = Decimal(str(details.get("defective_subtracted", 0)))
                additions_qty += def_sub
                
        elif op in ["SubtractStockQuantity", "AddDefectiveGoods", "PushToProduction"]:
            if op in ["AddDefectiveGoods", "PushToProduction"]:
                if op == "AddDefectiveGoods":
                    qty = Decimal(str(details.get("defective_added", 0)))
                else:
                    qty = Decimal(str(details.get("quantity_produced", 0)))
                consumption_qty += qty
                if op == "PushToProduction":
                    prod_cost = Decimal(str(details.get("total_production_cost", 0)))
                    consumption_amount += prod_cost
    
    return (additions_qty, additions_amount, consumption_qty, consumption_amount)

def build_report_for_period(start_date, end_date):
    """Build comprehensive report for date period - converted from Lambda function"""
    # TODO: migrate to Django ORM or RDS model
    # This would implement the main report building logic
    # - Fetch all stock items
    # - Calculate opening stock from saved snapshots
    # - Calculate inward movements (AddStockQuantity transactions)
    # - Calculate consumption (AddDefectiveGoods, PushToProduction)
    # - Calculate closing balances
    # - Group by stock groups and build hierarchy
    
    rows = []  # Placeholder for per-item rows
    totals = {
        "total_opening_stock_qty": 0,
        "total_opening_stock_amount": 0.0,
        "total_inward_qty": 0,
        "total_inward_amount": 0.0,
        "total_consumption_qty": 0,
        "total_consumption_amount": 0.0,
        "total_balance_qty": 0,
        "total_balance_amount": 0.0,
    }
    
    return rows, totals