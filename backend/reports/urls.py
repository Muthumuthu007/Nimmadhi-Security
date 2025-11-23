from django.urls import path
from . import views

urlpatterns = [
    # Stock reports
    path('daily/', views.get_daily_report, name='get_daily_report'),
    path('weekly/', views.get_weekly_report, name='get_weekly_report'),
    path('monthly/', views.get_monthly_report, name='get_monthly_report'),
    
    # Production reports
    path('production/daily/', views.get_daily_push_to_production, name='get_daily_push_to_production'),
    path('production/weekly/', views.get_weekly_push_to_production, name='get_weekly_push_to_production'),
    path('production/monthly/', views.get_monthly_push_to_production, name='get_monthly_push_to_production'),
    path('production/summary/monthly/', views.get_monthly_production_summary, name='get_monthly_production_summary'),
    
    # Consumption reports
    path('consumption/daily/', views.get_daily_consumption_summary, name='get_daily_consumption_summary'),
    path('consumption/weekly/', views.get_weekly_consumption_summary, name='get_weekly_consumption_summary'),
    path('consumption/monthly/', views.get_monthly_consumption_summary, name='get_monthly_consumption_summary'),
    
    # Inward reports
    path('inward/daily/', views.get_daily_inward, name='get_daily_inward'),
    path('inward/weekly/', views.get_weekly_inward, name='get_weekly_inward'),
    path('inward/monthly/', views.get_monthly_inward, name='get_monthly_inward'),
    
    # Transaction reports
    path('transactions/', views.get_all_stock_transactions, name='get_all_stock_transactions'),
    path('logs/today/', views.get_today_logs, name='get_today_logs'),
    path('item-history/', views.get_item_history, name='get_item_history'),
]