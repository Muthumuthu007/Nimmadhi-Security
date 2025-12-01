from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_user, name='register_user'),
    path('login/', views.login_user, name='login_user'),
    path('logout/', views.logout_user, name='logout_user'),
    path('admin/view/', views.admin_view_users, name='admin_view_users'),
    path('admin/update/', views.admin_update_user, name='admin_update_user'),
]