from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_grn, name='create_grn'),
    path('list/', views.list_all_grn, name='list_all_grn'),
    path('<str:grn_id>/', views.get_grn, name='get_grn'),
    path('<str:grn_id>/delete/', views.delete_grn, name='delete_grn'),
    path('transport/<str:transport_type>/', views.get_grn_by_transport, name='get_grn_by_transport'),
    path('supplier/<str:supplier_name>/', views.get_grn_by_supplier_name, name='get_grn_by_supplier_name'),
]