from django.urls import path
from . import views

app_name = 'delivery'

urlpatterns = [
    path('', views.dashboard, name='home'),  # Add home URL pattern
    path('register/', views.delivery_register, name='register'),
    path('login/', views.delivery_login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('orders/', views.orders, name='orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('history/', views.history, name='history'),
    path('earnings/', views.earnings, name='earnings'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings, name='settings'),
    path('toggle-status/', views.toggle_status, name='toggle_status'),
    path('fix-delivered/', views.fix_delivered_orders, name='fix_delivered_orders'),
]
