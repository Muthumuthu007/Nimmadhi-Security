"""
Daily Inward Service - Exact port from Lambda get_daily_inward function
Handles inward stock reporting with group hierarchy nesting
"""
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict
from backend.dynamodb_service import dynamodb_service
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger(__name__)

class InwardService:
    """Service class for inward stock reporting - exact Lambda port"""
    
    @staticmethod
    def _get_inward_data(start_date, end_date):
        """
        Aggregates inward stock data per item per date.
        Shows only stock name, quantities, cost and date.
        Exact port from Lambda _get_inward_data function.
        """
        result = {}
        
        # Format dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")
        
        # Scan AddStockQuantity transactions - exact Lambda filter
        transactions = dynamodb_service.scan_table(
            'stock_transactions',
            FilterExpression=Attr("operation_type").eq("AddStockQuantity") & Attr("date").between(start_str, end_str)
        )
        
        # Aggregate by date and item - exact Lambda logic
        aggregated = defaultdict(lambda: defaultdict(lambda: {
            "stock_name": "",
            "inward_quantity": 0,
            "added_cost": 0,
            "existing_quantity": None,
            "new_quantity": None
        }))
        
        for txn in transactions:
            date_str = txn.get("date")
            if not date_str:
                continue
                
            details = txn.get("details", {})
            item_id = details.get("item_id")
            quantity_added = float(details.get("quantity_added", 0))
            new_available = float(details.get("new_available", 0))
            added_cost = float(details.get("added_cost", 0))
            existing_qty = new_available - quantity_added
            
            # Fetch stock name from stock table - exact Lambda lookup
            stock_item = dynamodb_service.get_item('STOCK', {"item_id": item_id})
            stock_name = stock_item.get("name", item_id) if stock_item else item_id
            
            item = aggregated[date_str][item_id]
            item["stock_name"] = stock_name
            item["inward_quantity"] += quantity_added
            item["added_cost"] += added_cost
            item["new_quantity"] = new_available
            if item["existing_quantity"] is None:
                item["existing_quantity"] = existing_qty
        
        # Flatten into result[date] = [list of stock inward summaries] - exact Lambda format
        for date_str, items in aggregated.items():
            result[date_str] = []
            for item_id, data in items.items():
                result[date_str].append({
                    "stock_name": data["stock_name"],
                    "existing_quantity": data["existing_quantity"],
                    "inward_quantity": data["inward_quantity"],
                    "new_quantity": data["new_quantity"],
                    "added_cost": data["added_cost"],
                    "date": date_str
                })
        
        return result
    
    @staticmethod
    def get_group_chain(group_id):
        """
        Walk up Groups table to build [parent, ..., child] chain of names.
        Exact port from Lambda get_group_chain function.
        """
        chain = []
        while group_id:
            grp = dynamodb_service.get_item('GROUPS', {'group_id': group_id})
            if not grp:
                break
            chain.insert(0, grp['name'])
            group_id = grp.get('parent_id')
        return chain
    
    @classmethod
    def get_daily_inward(cls, report_date=None):
        """
        Daily inward, grouped by date → group → subgroup → [records…].
        Exact port from Lambda get_daily_inward function.
        
        Args:
            report_date (str, optional): Date in YYYY-MM-DD format. Defaults to today IST.
            
        Returns:
            dict: Nested inward data structure matching Lambda output
        """
        try:
            # 1) Parse report_date - exact Lambda logic
            if report_date is None:
                report_date = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")
            elif not isinstance(report_date, str):
                raise ValueError("report_date must be a string")
            report_date = report_date.strip()
            
            # 2) Fetch raw inward data for that single day - exact Lambda call
            raw = cls._get_inward_data(report_date, report_date)  # { "YYYY-MM-DD": [ {...}, ... ] }
            
            # 3) Lookup groups & nest - exact Lambda logic
            nested = {}
            for dt, records in raw.items():
                grouped = {}
                for rec in records:
                    # Find the stock item to get group_id - exact Lambda lookup
                    stock_items = dynamodb_service.scan_table(
                        'STOCK',
                        FilterExpression=Attr("name").eq(rec["stock_name"])
                    )
                    item = stock_items[0] if stock_items else None
                    group_id = item.get("group_id") if item else None
                    
                    # Build chain - exact Lambda chain building
                    chain = cls.get_group_chain(group_id) if group_id else []
                    grp = chain[0] if len(chain) >= 1 else "Unknown"
                    sub = chain[1] if len(chain) >= 2 else "Unknown"
                    
                    # Nest under grouped[grp][sub] - exact Lambda nesting
                    grouped.setdefault(grp, {}).setdefault(sub, []).append(rec)
                
                nested[dt] = grouped
            
            # 4) Return - exact Lambda payload format
            payload = {
                "report_period": {"start_date": report_date, "end_date": report_date},
                "inward": nested
            }
            return payload
            
        except Exception as e:
            logger.error(f"Error in get_daily_inward: {e}", exc_info=True)
            raise
    
    @classmethod
    def get_weekly_inward(cls, start_date=None, end_date=None):
        """
        Weekly inward, grouped date-wise → group → subgroup → [records…].
        Exact port from Lambda get_weekly_inward function.
        """
        try:
            # 1) Determine IST date window - exact Lambda logic
            now = datetime.utcnow() + timedelta(hours=5, minutes=30)
            if end_date is None:
                end_date = now.strftime("%Y-%m-%d")
            if start_date is None:
                start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
            
            start_date = start_date.strip()
            end_date = end_date.strip()
            
            # Parse into date objects
            sd_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            ed_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            # 2) Fetch raw inward data for the range - exact Lambda call
            raw = cls._get_inward_data(start_date, end_date)  # { date: [ {...}, ... ] }
            
            # 3) Initialize nested structure with all dates in range - exact Lambda logic
            nested = {}
            cur = sd_dt
            while cur <= ed_dt:
                nested[cur.strftime("%Y-%m-%d")] = {}
                cur += timedelta(days=1)
            
            # 4) Enrich and group - exact Lambda logic
            for dt, recs in raw.items():
                for rec in recs:
                    item_id = rec["stock_name"]  # Note: Lambda uses stock_name as lookup key
                    
                    # Lookup group_id by item_id - exact Lambda lookup
                    stock_item = dynamodb_service.get_item('STOCK', {"item_id": item_id})
                    group_id = stock_item.get("group_id") if stock_item else None
                    
                    # Build group chain - exact Lambda chain building
                    chain = cls.get_group_chain(group_id) if group_id else []
                    grp = chain[0] if len(chain) >= 1 else "Unknown"
                    sub = chain[1] if len(chain) >= 2 else "Unknown"
                    
                    # Insert rec under nested[dt][grp][sub] - exact Lambda nesting
                    nested.setdefault(dt, {}).setdefault(grp, {}).setdefault(sub, []).append(rec)
            
            # 5) Compute grand totals - exact Lambda calculation
            total_qty = 0
            total_amt = Decimal("0")
            for dt_recs in nested.values():
                for grp_recs in dt_recs.values():
                    for sub_recs in grp_recs.values():
                        for rec in sub_recs:
                            total_qty += rec.get("inward_quantity", 0)
                            total_amt += Decimal(str(rec.get("added_cost", 0)))
            
            # 6) Return payload - exact Lambda format
            payload = {
                "report_period": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "inward": nested,
                "total_inward_quantity": float(total_qty),
                "total_inward_amount": float(total_amt)
            }
            return payload
            
        except Exception as e:
            logger.error(f"Error in get_weekly_inward: {e}", exc_info=True)
            raise