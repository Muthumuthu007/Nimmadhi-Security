from django.urls import path
from . import views

urlpatterns = [
    # Group management
    path('groups/', views.list_groups, name='list_groups_short'),
    path('groups/create/', views.create_group, name='create_group'),
    path('groups/delete/', views.delete_group, name='delete_group'),
    path('groups/list/', views.list_groups, name='list_groups'),
    path('groups/listgroups/', views.listgroups, name='listgroups'),
    
    # Stock management
    path('create/', views.create_stock, name='create_stock'),
    path('update/', views.update_stock, name='update_stock'),
    path('delete/', views.delete_stock, name='delete_stock'),
    path('list/', views.get_all_stocks, name='get_all_stocks'),
    path('inventory/', views.list_inventory_stock, name='list_inventory_stock'),
    path('add-quantity/', views.add_stock_quantity, name='add_stock_quantity'),
    path('subtract-quantity/', views.subtract_stock_quantity, name='subtract_stock_quantity'),
    path('add-defective/', views.add_defective_goods, name='add_defective_goods'),
    path('subtract-defective/', views.subtract_defective_goods, name='subtract_defective_goods'),
    
    # Stock descriptions
    path('descriptions/create/', views.create_description, name='create_description'),
    path('descriptions/get/', views.get_description, name='get_description'),
    path('descriptions/list/', views.get_all_descriptions, name='get_all_descriptions'),
    
    # Stock snapshots
    path('opening-stock/', views.save_opening_stock, name='save_opening_stock'),
    path('closing-stock/', views.save_closing_stock, name='save_closing_stock'),
    
    # Production management
    path('products/create/', views.create_product, name='create_product'),
    path('products/update/', views.update_product, name='update_product'),
    path('products/update-details/', views.update_product_details, name='update_product_details'),
    path('products/delete/', views.delete_product, name='delete_product'),
    path('products/list/', views.get_all_products, name='get_all_products'),
    path('products/alter/', views.alter_product_components, name='alter_product_components'),
    path('production/push/', views.push_to_production, name='push_to_production'),
    path('production/undo/', views.undo_production, name='undo_production'),
    path('production/delete/', views.delete_push_to_production, name='delete_push_to_production'),
    
    # Transactions
    path('transactions/', views.get_all_stock_transactions, name='get_all_stock_transactions'),
    
    # Actions
    path('undo/', views.undo_action, name='undo_action'),
    path('admin/delete-transactions/', views.delete_transaction_data, name='delete_transaction_data'),
    
    # Debug endpoints
    path('debug/stock-items/', views.debug_stock_items, name='debug_stock_items'),
    path('debug/test-lookup/', views.test_stock_lookup, name='test_stock_lookup'),
]