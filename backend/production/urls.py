from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_product, name='create_product'),
    path('update/', views.update_product, name='update_product'),
    path('delete/', views.delete_product, name='delete_product'),
    path('list/', views.get_all_products, name='get_all_products'),
    path('alter/', views.alter_product_components, name='alter_product_components'),
    path('update-details/', views.update_product_details, name='update_product_details'),

    path('push/', views.push_to_production, name='push_to_production'),
    path('undo/', views.undo_production, name='undo_production'),
    path('delete-push/', views.delete_push_to_production, name='delete_push_to_production'),
    path('daily/', views.get_daily_push_to_production, name='get_daily_push_to_production'),
    path('weekly/', views.get_weekly_push_to_production, name='get_weekly_push_to_production'),
    path('monthly/', views.get_monthly_push_to_production, name='get_monthly_push_to_production'),
    path('monthly-public/', views.get_monthly_push_to_production_public, name='get_monthly_push_to_production_public'),
]