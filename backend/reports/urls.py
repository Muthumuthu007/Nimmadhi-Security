from django.urls import path
from . import views
from . import normal_reports

urlpatterns = [
    # Stock reports - comprehensive daily report including inward and consumption
    path('daily/', views.get_daily_consumption_summary, name='get_daily_report'),
    path('weekly/', views.get_weekly_consumption_summary, name='get_weekly_report'),
    path('monthly/', views.get_monthly_consumption_summary, name='get_monthly_report'),
    
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
    path('inward/monthly-grid/', views.get_monthly_inward_grid, name='get_monthly_inward_grid'),
    
    # Outward reports
    path('outward/monthly-grid/', views.get_monthly_outward_grid, name='get_monthly_outward_grid'),
    
    # Transaction reports
    path('transactions/', views.get_all_stock_transactions, name='get_all_stock_transactions'),
    path('logs/today/', views.get_today_logs, name='get_today_logs'),
    path('item-history/', views.get_item_history, name='get_item_history'),
    
    # GRN reports
    # path('grn/supplier/', views.get_grn_by_supplier_name, name='get_grn_by_supplier_name'),  # Function not implemented yet
    
    # Normal reports (Lambda-style)
    path('normal/daily/', normal_reports.get_daily_report, name='get_normal_daily_report'),
    path('normal/weekly/', normal_reports.get_weekly_report, name='get_normal_weekly_report'),
    path('normal/monthly/', normal_reports.get_monthly_report, name='get_normal_monthly_report'),
]