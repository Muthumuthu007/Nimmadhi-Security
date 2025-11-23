from decimal import Decimal
from django.db import transaction
from .models import Product, PushToProduction
from stock.models import Stock
import logging

logger = logging.getLogger(__name__)

def recalc_max_produce(product_id):
    """Recalculate max_produce for a product based on current stock"""
    try:
        product = Product.objects.get(product_id=product_id)
        stock_needed = product.stock_needed
        max_produce = None
        
        for item_id, qty_str in stock_needed.items():
            qty_needed = Decimal(str(qty_str))
            try:
                stock_item = Stock.objects.get(item_id=item_id)
                available_qty = Decimal(str(stock_item.quantity))
                possible = available_qty // qty_needed
                if max_produce is None or possible < max_produce:
                    max_produce = possible
            except Stock.DoesNotExist:
                max_produce = 0
                break
        
        if max_produce is None:
            max_produce = 0
            
        product.max_produce = int(max_produce)
        product.save()
    except Product.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error in recalc_max_produce: {str(e)}")

def recalc_all_production():
    """Recalculate max_produce for all products"""
    try:
        products = Product.objects.all()
        for product in products:
            recalc_max_produce(product.product_id)
    except Exception as e:
        logger.error(f"Error in recalc_all_production: {str(e)}")

def get_group_chain(group_id):
    """Walk up the Groups table to build [parent, …, child] chain of names"""
    from users.models import Group
    chain = []
    while group_id:
        try:
            group = Group.objects.get(group_id=group_id)
            chain.insert(0, group.name)
            group_id = group.parent_id
        except Group.DoesNotExist:
            break
    return chain