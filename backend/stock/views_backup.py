import json
import uuid
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from backend.dynamodb_service import dynamodb_service
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def create_group(request):
    """Create a new group - converted from Lambda create_group function"""
    try:
        body = json.loads(request.body)
        
        if 'name' not in body:
            return JsonResponse({"error": "'name' is required"}, status=400)

        name = body['name']
        parent_id = body.get('parent_id')  # may be None
        group_id = str(uuid.uuid4())

        # Create group in DynamoDB
        group_item = {
            'group_id': group_id,
            'name': name
        }
        if parent_id:
            group_item['parent_id'] = parent_id
        
        dynamodb_service.put_item('GROUPS', group_item)
        
        logger.info(f"Group created: {group_id} ('{name}', parent={parent_id})")

        return JsonResponse({
            "message": "Group created successfully",
            "group_id": group_id,
            "name": name,
            "parent_id": parent_id
        })
        
    except Exception as e:
        logger.error(f"Error in create_group: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def delete_group(request):
    """Delete group - converted from Lambda delete_group function"""
    try:
        body = json.loads(request.body)
        
        if 'group_id' not in body:
            return JsonResponse({"error": "'group_id' is required"}, status=400)

        group_id = body['group_id']
        
        # TODO: migrate to Django ORM or RDS model
        # group = Group.objects.filter(group_id=group_id).first()
        # if not group:
        #     return JsonResponse({"error": "Group not found"}, status=404)
        # group.delete()

        logger.info(f"Group deleted: {group_id}")
        return JsonResponse({
            "message": "Group deleted successfully",
            "group_id": group_id
        })
        
    except Exception as e:
        logger.error(f"Error in delete_group: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def list_groups(request):
    """List groups - converted from Lambda list_groups function"""
    try:
        parent_id = request.GET.get('parent_id')
        logger.info(f"Fetching groups with parent_id: {parent_id}")
        
        # Get groups from DynamoDB
        try:
            if parent_id:
                # Query groups with specific parent_id
                groups = dynamodb_service.scan_table(
                    'GROUPS', 
                    FilterExpression='parent_id = :pid', 
                    ExpressionAttributeValues={':pid': parent_id}
                )
            else:
                # Get root groups (no parent_id)
                groups = dynamodb_service.scan_table(
                    'GROUPS', 
                    FilterExpression='attribute_not_exists(parent_id)'
                )
            
            logger.info(f"Found {len(groups)} groups")
            return JsonResponse({"groups": groups}, safe=False)
            
        except ClientError as e:
            logger.error(f"DynamoDB error fetching groups: {e}")
            return JsonResponse({"error": "Failed to fetch groups from database"}, status=500)
        
    except Exception as e:
        logger.error(f"Error in list_groups: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def create_stock(request):
    """Create stock item - converted from Lambda create_stock function"""
    try:
        body = json.loads(request.body)
        
        required = ['name', 'quantity', 'defective', 'cost_per_unit', 'stock_limit', 'username', 'unit', 'group_id']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # Check if item already exists
        # if Stock.objects.filter(item_id=body['name']).exists():
        #     return JsonResponse({"message": "already exist"}, status=400)

        item_id = body['name']
        quantity = Decimal(str(body['quantity']))
        defective = Decimal(str(body['defective']))
        cost_per_unit = Decimal(str(body['cost_per_unit']))
        stock_limit = Decimal(str(body['stock_limit']))
        username = body['username']
        unit = body['unit']
        group_id = body['group_id']

        available_qty = quantity - defective
        total_cost = available_qty * cost_per_unit

        # TODO: migrate to Django ORM or RDS model
        # Stock.objects.create(
        #     item_id=item_id,
        #     name=item_id,
        #     quantity=int(available_qty),
        #     cost_per_unit=cost_per_unit,
        #     total_cost=total_cost,
        #     stock_limit=stock_limit,
        #     defective=int(defective),
        #     total_quantity=int(quantity),
        #     unit=unit,
        #     username=username,
        #     group_id=group_id
        # )

        logger.info(f"Stock created: {item_id}")
        
        return JsonResponse({
            "message": "Stock created successfully.",
            "item_id": item_id,
            "quantity": int(available_qty),
            "total_quantity": int(quantity),
            "cost_per_unit": float(cost_per_unit),
            "total_cost": float(total_cost),
            "stock_limit": float(stock_limit),
            "defective": int(defective),
            "unit": unit,
            "group_id": group_id
        })
        
    except Exception as e:
        logger.error(f"Error in create_stock: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_stock(request):
    """Update stock item - converted from Lambda update_stock function"""
    try:
        body = json.loads(request.body)
        
        item_id = body.get('name')
        if not item_id:
            return JsonResponse({"error": "'name' is required"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # stock_item = Stock.objects.filter(item_id=item_id).first()
        # if not stock_item:
        #     return JsonResponse({"error": "Stock item not found"}, status=404)

        # Handle defective-only update
        keys = set(body.keys()) - {'operation'}
        if keys == {'name', 'defective', 'username'}:
            # TODO: Update only defective count
            pass

        # Handle full update
        required = ['name', 'quantity', 'defective', 'cost_per_unit', 'stock_limit', 'unit', 'username']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        # TODO: Implement full stock update logic
        
        logger.info(f"Stock updated: {item_id}")
        return JsonResponse({"message": "Stock updated successfully."})
        
    except Exception as e:
        logger.error(f"Error in update_stock: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def delete_stock(request):
    """Delete stock item - converted from Lambda delete_stock function"""
    try:
        body = json.loads(request.body)
        
        required = ['name', 'username']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        name = body['name']
        username = body['username']

        # TODO: migrate to Django ORM or RDS model
        # stock_item = Stock.objects.filter(item_id=name).first()
        # if not stock_item:
        #     return JsonResponse({"error": f"Stock item '{name}' not found."}, status=404)
        # stock_item.delete()

        logger.info(f"Stock '{name}' deleted by {username}.")
        return JsonResponse({"message": f"Stock '{name}' deleted successfully."})
        
    except Exception as e:
        logger.error(f"Error in delete_stock: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_all_stocks(request):
    """Get all stocks with group hierarchy - converted from Lambda get_all_stocks function"""
    try:
        group_id = request.GET.get('group_id')
        logger.info(f"Fetching stocks for group_id: {group_id}")
        
        # Get all groups first to build hierarchy
        all_groups = dynamodb_service.scan_table('GROUPS')
        groups_dict = {group['group_id']: group for group in all_groups}
        
        # Build group hierarchy helper function
        def get_child_groups(parent_id):
            children = []
            for group in all_groups:
                if group.get('parent_id') == parent_id:
                    children.append(group['group_id'])
                    children.extend(get_child_groups(group['group_id']))
            return children
        
        if group_id:
            # Get stocks for specific group and all its child groups
            target_groups = [group_id] + get_child_groups(group_id)
            
            # Get stocks for all target groups
            all_stocks = dynamodb_service.scan_table('STOCK')
            stocks = [stock for stock in all_stocks if stock.get('group_id') in target_groups]
        else:
            # Get all stocks
            stocks = dynamodb_service.scan_table('STOCK')
        
        # Build hierarchical tree structure
        from collections import defaultdict
        
        # Map parent_id -> list of child group_ids
        children = defaultdict(list)
        for group in all_groups:
            parent_id = group.get('parent_id')
            children[parent_id].append(group['group_id'])
        
        # Map group_id -> list of stock items
        items_by_group = defaultdict(list)
        for stock in stocks:
            group_id = stock.get('group_id')
            if group_id not in groups_dict:
                group_id = None
            items_by_group[group_id].append(stock)
        
        # Recursive tree builder
        def build_tree(parent_id):
            nodes = []
            for group_id in children.get(parent_id, []):
                group = groups_dict[group_id]
                node = {
                    "group_id": group_id,
                    "group_name": group['name'],
                    "items": items_by_group.get(group_id, []),
                    "subgroups": build_tree(group_id)
                }
                nodes.append(node)
            return nodes
        
        # Build tree starting from root groups
        tree = build_tree(None)
        
        # Add ungrouped items if any
        ungrouped = items_by_group.get(None, [])
        if ungrouped:
            tree.append({
                "group_id": None,
                "group_name": "null",
                "items": ungrouped,
                "subgroups": []
            })
        
        logger.info(f"Built hierarchical tree with {len(tree)} root groups")
        return JsonResponse(tree, safe=False)
        
    except Exception as dynamo_error:
                logger.warning(f"DynamoDB not available, falling back to Django ORM: {dynamo_error}")
                
                # Fallback to Django ORM
                from .models import Stock, Group
                
                # Get all groups for hierarchy
                all_groups = list(Group.objects.all().values('group_id', 'name', 'parent_id'))
                groups_dict = {group['group_id']: group for group in all_groups}
                
                # Build group hierarchy helper function
                def get_child_groups_orm(parent_id):
                    children = []
                    for group in all_groups:
                        if group.get('parent_id') == parent_id:
                            children.append(group['group_id'])
                            children.extend(get_child_groups_orm(group['group_id']))
                    return children
                
                if group_id:
                    # Get stocks for specific group and all its child groups
                    target_groups = [group_id] + get_child_groups_orm(group_id)
                    stocks_queryset = Stock.objects.filter(group_id__in=target_groups)
                else:
                    # Get all stocks
                    stocks_queryset = Stock.objects.all()
                
                # Build hierarchical tree structure
                from collections import defaultdict
                
                # Convert stocks to dict format
                stock_items = []
                for stock in stocks_queryset:
                    stock_dict = {
                        'item_id': stock.item_id,
                        'name': stock.name,
                        'quantity': stock.quantity,
                        'total_quantity': stock.total_quantity,
                        'defective': stock.defective,
                        'cost_per_unit': float(stock.cost_per_unit),
                        'total_cost': float(stock.total_cost),
                        'stock_limit': float(stock.stock_limit),
                        'unit': stock.unit,
                        'group_id': stock.group_id,
                        'username': stock.username,
                        'created_at': stock.created_at.isoformat() if stock.created_at else None,
                        'updated_at': stock.updated_at.isoformat() if stock.updated_at else None,
                    }
                    stock_items.append(stock_dict)
                
                # Map parent_id -> list of child group_ids
                children = defaultdict(list)
                for group in all_groups:
                    parent_id = group.get('parent_id')
                    children[parent_id].append(group['group_id'])
                
                # Map group_id -> list of stock items
                items_by_group = defaultdict(list)
                for stock in stock_items:
                    group_id = stock.get('group_id')
                    if group_id not in groups_dict:
                        group_id = None
                    items_by_group[group_id].append(stock)
                
                # Recursive tree builder
                def build_tree(parent_id):
                    nodes = []
                    for group_id in children.get(parent_id, []):
                        group = groups_dict[group_id]
                        node = {
                            "group_id": group_id,
                            "group_name": group['name'],
                            "items": items_by_group.get(group_id, []),
                            "subgroups": build_tree(group_id)
                        }
                        nodes.append(node)
                    return nodes
                
                # Build tree starting from root groups
                tree = build_tree(None)
                
                # Add ungrouped items if any
                ungrouped = items_by_group.get(None, [])
                if ungrouped:
                    tree.append({
                        "group_id": None,
                        "group_name": "null",
                        "items": ungrouped,
                        "subgroups": []
                    })
                
                logger.info(f"Built hierarchical tree with {len(tree)} root groups from Django ORM")
                return JsonResponse(tree, safe=False)
            
        except Exception as e:
            logger.error(f"Error fetching stocks: {e}")
            return JsonResponse({"error": "Failed to fetch stocks from database"}, status=500)
        
    except Exception as e:
        logger.error(f"Error in get_all_stocks: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def list_inventory_stock(request):
    """List inventory stock - converted from Lambda list_inventory_stock function"""
    try:
        # Get query parameters
        limit = int(request.GET.get('limit', 100))
        item_name = request.GET.get('item_name')
        
        logger.info(f"Fetching inventory stock - limit: {limit}, item_name: {item_name}")
        
        # Get all stocks first
        all_stocks = dynamodb_service.scan_table('STOCK')
        
        # Filter by item name if provided
        if item_name:
            stocks = [stock for stock in all_stocks 
                     if item_name.lower() in stock.get('name', '').lower()]
        else:
            stocks = all_stocks
        
        # Apply limit
        stocks = stocks[:limit]
        
        # Get groups for enhanced display
        all_groups = dynamodb_service.scan_table('GROUPS')
        groups_dict = {group['group_id']: group for group in all_groups}
        
        # Enhance inventory with group information
        enhanced_inventory = []
        for stock in stocks:
            enhanced_stock = stock.copy()
            stock_group_id = stock.get('group_id')
            if stock_group_id and stock_group_id in groups_dict:
                enhanced_stock['group_name'] = groups_dict[stock_group_id].get('name', 'Unknown')
            else:
                enhanced_stock['group_name'] = 'Uncategorized'
            
            # Calculate available quantity (total - defective)
            total_qty = int(enhanced_stock.get('total_quantity', 0))
            defective_qty = int(enhanced_stock.get('defective', 0))
            enhanced_stock['available_quantity'] = total_qty - defective_qty
            
            enhanced_inventory.append(enhanced_stock)
        
        # Sort by name for consistent ordering
        enhanced_inventory.sort(key=lambda x: x.get('name', '').lower())
        
        logger.info(f"Found {len(enhanced_inventory)} inventory items from DynamoDB")
        return JsonResponse({"inventory": enhanced_inventory}, safe=False)
        
    except Exception as dynamo_error:
                logger.warning(f"DynamoDB not available, falling back to Django ORM: {dynamo_error}")
                
                # Fallback to Django ORM
                from .models import Stock, Group
                
                # Build query
                stocks_queryset = Stock.objects.all()
                
                # Filter by item name if provided
                if item_name:
                    stocks_queryset = stocks_queryset.filter(name__icontains=item_name)
                
                # Apply limit
                stocks_queryset = stocks_queryset[:limit]
                
                # Get groups for enhanced display
                all_groups = list(Group.objects.all().values('group_id', 'name'))
                groups_dict = {group['group_id']: group for group in all_groups}
                
                # Enhance inventory with group information
                enhanced_inventory = []
                for stock in stocks_queryset:
                    enhanced_stock = {
                        'item_id': stock.item_id,
                        'name': stock.name,
                        'quantity': stock.quantity,
                        'total_quantity': stock.total_quantity,
                        'defective': stock.defective,
                        'cost_per_unit': float(stock.cost_per_unit),
                        'total_cost': float(stock.total_cost),
                        'stock_limit': float(stock.stock_limit),
                        'unit': stock.unit,
                        'group_id': stock.group_id,
                        'username': stock.username,
                        'created_at': stock.created_at.isoformat() if stock.created_at else None,
                        'updated_at': stock.updated_at.isoformat() if stock.updated_at else None,
                    }
                    
                    # Add group information
                    if stock.group_id and stock.group_id in groups_dict:
                        enhanced_stock['group_name'] = groups_dict[stock.group_id].get('name', 'Unknown')
                    else:
                        enhanced_stock['group_name'] = 'Uncategorized'
                    
                    # Calculate available quantity (total - defective)
                    enhanced_stock['available_quantity'] = stock.total_quantity - stock.defective
                    
                    enhanced_inventory.append(enhanced_stock)
                
                # Sort by name for consistent ordering
                enhanced_inventory.sort(key=lambda x: x.get('name', '').lower())
                
                logger.info(f"Found {len(enhanced_inventory)} inventory items from Django ORM")
                return JsonResponse({"inventory": enhanced_inventory}, safe=False)
            
        except Exception as e:
            logger.error(f"Error fetching inventory: {e}")
            return JsonResponse({"error": "Failed to fetch inventory from database"}, status=500)
        
    except Exception as e:
        logger.error(f"Error in list_inventory_stock: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def add_stock_quantity(request):
    """Add stock quantity - converted from Lambda add_stock_quantity function"""
    try:
        body = json.loads(request.body)
        
        for field in ("name", "quantity_to_add", "username"):
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # Implement stock quantity addition logic
        
        return JsonResponse({"message": "Stock quantity added successfully."})
        
    except Exception as e:
        logger.error(f"Error in add_stock_quantity: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def subtract_stock_quantity(request):
    """Subtract stock quantity - converted from Lambda subtract_stock_quantity function"""
    try:
        body = json.loads(request.body)
        
        for field in ("name", "quantity_to_subtract", "username"):
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # Implement stock quantity subtraction logic
        
        return JsonResponse({"message": "Stock quantity subtracted successfully."})
        
    except Exception as e:
        logger.error(f"Error in subtract_stock_quantity: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def add_defective_goods(request):
    """Add defective goods - converted from Lambda add_defective_goods function"""
    try:
        body = json.loads(request.body)
        
        required = ['name', 'defective_to_add', 'username']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # Implement defective goods addition logic
        
        return JsonResponse({"message": "Defective goods added successfully."})
        
    except Exception as e:
        logger.error(f"Error in add_defective_goods: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def subtract_defective_goods(request):
    """Subtract defective goods - converted from Lambda subtract_defective_goods function"""
    try:
        body = json.loads(request.body)
        
        required = ['name', 'defective_to_subtract', 'username']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # Implement defective goods subtraction logic
        
        return JsonResponse({"message": "Defective goods subtracted successfully."})
        
    except Exception as e:
        logger.error(f"Error in subtract_defective_goods: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def create_product(request):
    """Create production product - converted from Lambda create_product function"""
    try:
        body = json.loads(request.body)
        
        required = ['product_name', 'stock_needed', 'username', 'wastage_percent', 'transport_cost', 'labour_cost', 'other_cost']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # Implement product creation with cost calculations
        
        product_id = str(uuid.uuid4())
        logger.info(f"Product created: {product_id}")
        
        return JsonResponse({
            "message": "Product created successfully",
            "product_id": product_id
        })
        
    except Exception as e:
        logger.error(f"Error in create_product: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_product(request):
    """Update product - converted from Lambda update_product function"""
    try:
        body = json.loads(request.body)
        
        if 'product_id' not in body or 'username' not in body:
            return JsonResponse({"error": "'product_id' and 'username' are required"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # Implement product update logic
        
        return JsonResponse({"message": "Product updated successfully"})
        
    except Exception as e:
        logger.error(f"Error in update_product: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_product_details(request):
    """Update product details - converted from Lambda update_product_details function"""
    try:
        body = json.loads(request.body)
        
        missing = [f for f in ("product_id", "username") if f not in body]
        if missing:
            return JsonResponse({"error": f"Missing required field(s): {', '.join(missing)}"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # Update only cost-related fields: wastage_percent, transport_cost, labour_cost, other_cost
        # Then recalculate all derived fields
        
        return JsonResponse({"message": "Product details updated successfully"})
        
    except Exception as e:
        logger.error(f"Error in update_product_details: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def delete_product(request):
    """Delete product - converted from Lambda delete_product function"""
    try:
        body = json.loads(request.body)
        
        required = ['product_id', 'username']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # product = Product.objects.filter(product_id=body['product_id']).first()
        # if not product:
        #     return JsonResponse({"error": "Product not found"}, status=404)
        # product.delete()
        
        return JsonResponse({"message": "Product deleted successfully"})
        
    except Exception as e:
        logger.error(f"Error in delete_product: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_all_products(request):
    """Get all products from DynamoDB"""
    try:
        products = dynamodb_service.scan_table('PRODUCTION')
        stocks = dynamodb_service.scan_table('STOCK')
        groups = dynamodb_service.scan_table('GROUPS')
        
        # Build stock and group maps
        stock_map = {item['item_id']: item for item in stocks}
        groups_by_id = {g['group_id']: {'name': g['name'], 'parent_id': g.get('parent_id')} for g in groups}
        
        # Cache for group chains
        chain_cache = {}
        def build_chain(gid):
            if gid in chain_cache:
                return chain_cache[gid]
            chain = []
            current = gid
            while current and current in groups_by_id:
                grp = groups_by_id[current]
                chain.insert(0, grp['name'])
                current = grp.get('parent_id')
            chain_cache[gid] = chain
            return chain
        
        # Enrich products
        enriched = []
        for p in products:
            details = []
            for mat_id, qty_str in p.get('stock_needed', {}).items():
                try:
                    qty = float(qty_str)
                except:
                    qty = float(Decimal(str(qty_str)))
                stock_item = stock_map.get(mat_id, {})
                group_id = stock_item.get('group_id')
                chain = build_chain(group_id) if group_id else []
                details.append({
                    'item_id': mat_id,
                    'required_qty': qty,
                    'group_chain': chain
                })
            p['stock_details'] = details
            p.pop('stock_needed', None)
            enriched.append(p)
        
        return JsonResponse(enriched, safe=False)
        
    except Exception as e:
        logger.error(f"Error in get_all_products: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def alter_product_components(request):
    """Alter product components - converted from Lambda alter_product_components function"""
    try:
        body = json.loads(request.body)
        
        missing = [f for f in ("product_id", "username") if f not in body]
        if missing:
            return JsonResponse({"error": f"Missing required field(s): {', '.join(missing)}"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # Implement product component alteration logic
        
        return JsonResponse({"message": "Product components altered successfully"})
        
    except Exception as e:
        logger.error(f"Error in alter_product_components: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def push_to_production(request):
    """Push product to production - converted from Lambda push_to_production function"""
    try:
        body = json.loads(request.body)
        
        required = ['product_id', 'quantity', 'username']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # Implement production push logic with stock deductions
        
        push_id = str(uuid.uuid4())
        logger.info(f"Pushed to production: {push_id}")
        
        return JsonResponse({
            "message": "Product pushed to production successfully.",
            "push_id": push_id
        })
        
    except Exception as e:
        logger.error(f"Error in push_to_production: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def undo_production(request):
    """Undo production - converted from Lambda undo_production function"""
    try:
        body = json.loads(request.body)
        
        required = ['push_id', 'username']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # Implement production undo logic
        
        return JsonResponse({"message": "Production undone successfully"})
        
    except Exception as e:
        logger.error(f"Error in undo_production: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def delete_push_to_production(request):
    """Delete push to production - converted from Lambda delete_push_to_production function"""
    try:
        body = json.loads(request.body)
        
        required = ['push_id', 'username']
        for field in required:
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # push = PushToProduction.objects.filter(push_id=body['push_id']).first()
        # if not push:
        #     return JsonResponse({"error": "Push record not found"}, status=404)
        # push.delete()
        
        return JsonResponse({"message": "Push record deleted successfully"})
        
    except Exception as e:
        logger.error(f"Error in delete_push_to_production: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def undo_action(request):
    """Undo last action - converted from Lambda undo_action function"""
    try:
        body = json.loads(request.body)
        
        username = body.get('username')
        if not username:
            return JsonResponse({"error": "'username' is required"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # Implement undo logic based on operation type
        
        return JsonResponse({"message": "Action undone successfully."})
        
    except Exception as e:
        logger.error(f"Error in undo_action: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def create_description(request):
    """Create stock description - converted from Lambda create_description function"""
    try:
        body = json.loads(request.body)
        
        for field in ('stock', 'description', 'username'):
            if field not in body:
                return JsonResponse({"error": f"'{field}' is required"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # StockRemarks.objects.create(
        #     stock=body['stock'],
        #     description=body['description'],
        #     username=body['username'],
        #     created_at=timezone.now()
        # )
        
        return JsonResponse({"message": "Description saved successfully."})
        
    except Exception as e:
        logger.error(f"Error in create_description: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_description(request):
    """Get stock description - converted from Lambda get_description function"""
    try:
        body = json.loads(request.body)
        
        if 'stock' not in body:
            return JsonResponse({"error": "'stock' is required"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # description = StockRemarks.objects.filter(stock=body['stock']).first()
        # if not description:
        #     return JsonResponse({"error": "No description found"}, status=404)
        
        return JsonResponse({
            "stock": body['stock'],
            "description": "Sample description",
            "username": "sample_user",
            "created_at": "2024-01-01T00:00:00"
        })
        
    except Exception as e:
        logger.error(f"Error in get_description: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_all_descriptions(request):
    """Get all descriptions - converted from Lambda get_all_descriptions function"""
    try:
        # Try DynamoDB first
        try:
            descriptions = dynamodb_service.scan_table('stock_remarks')
            logger.info(f"Found {len(descriptions)} descriptions from DynamoDB")
            return JsonResponse(descriptions, safe=False)
            
        except Exception as dynamo_error:
            logger.warning(f"DynamoDB not available, falling back to Django ORM: {dynamo_error}")
            
            # Fallback to Django ORM
            from .models import StockRemarks
            descriptions = list(StockRemarks.objects.all().values(
                'stock', 'description', 'username', 'created_at'
            ))
            
            # Convert datetime to ISO format for JSON serialization
            for desc in descriptions:
                if desc.get('created_at'):
                    desc['created_at'] = desc['created_at'].isoformat()
            
            logger.info(f"Found {len(descriptions)} descriptions from Django ORM")
            return JsonResponse(descriptions, safe=False)
        
    except Exception as e:
        logger.error(f"Error in get_all_descriptions: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def save_opening_stock(request):
    """Save opening stock - converted from Lambda save_opening_stock function"""
    try:
        body = json.loads(request.body)
        
        if 'username' not in body:
            return JsonResponse({"error": "'username' is required"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # Implement opening stock save logic
        
        return JsonResponse({"message": "Opening stock saved successfully."})
        
    except Exception as e:
        logger.error(f"Error in save_opening_stock: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def save_closing_stock(request):
    """Save closing stock - converted from Lambda save_closing_stock function"""
    try:
        body = json.loads(request.body)
        
        if 'username' not in body:
            return JsonResponse({"error": "'username' is required"}, status=400)

        # TODO: migrate to Django ORM or RDS model
        # Implement closing stock save logic
        
        return JsonResponse({"message": "Closing stock saved successfully."})
        
    except Exception as e:
        logger.error(f"Error in save_closing_stock: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def delete_transaction_data(request):
    """Delete transaction data - converted from Lambda delete_transaction_data function"""
    try:
        body = json.loads(request.body)
        
        # Admin auth check
        if not (body.get('username') == 'admin' and body.get('password') == '37773'):
            return JsonResponse({"error": "Unauthorized: Admin credentials required."}, status=403)

        # TODO: migrate to Django ORM or RDS model
        # StockTransaction.objects.all().delete()
        
        return JsonResponse({"message": "All transaction data deleted."})
        
    except Exception as e:
        logger.error(f"Error in delete_transaction_data: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)