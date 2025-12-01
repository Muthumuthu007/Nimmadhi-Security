"""
Freight URL Configuration
"""
from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_freight_note, name='create_freight_note'),
    path('get/', views.get_freight_note, name='get_freight_note'),
    path('list/', views.list_freight_notes, name='list_freight_notes'),
    path('update/', views.update_freight_note, name='update_freight_note'),
    path('delete/', views.delete_freight_note, name='delete_freight_note'),
]