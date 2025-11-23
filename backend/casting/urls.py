from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_casting_product, name='create_casting_product'),
    path('move-to-production/', views.move_to_production, name='move_to_production'),
    path('delete/', views.delete_casting_product, name='delete_casting_product'),
    path('list/', views.get_all_casting_products, name='get_all_casting_products'),
]