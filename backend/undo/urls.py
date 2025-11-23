from django.urls import path
from . import views

urlpatterns = [
    path('action/', views.undo_action, name='undo_action'),
    path('delete-transactions/', views.delete_transaction_data, name='delete_transaction_data'),
]