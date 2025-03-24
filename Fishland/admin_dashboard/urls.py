from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('users/', views.users, name='users'),
    path('users/<int:user_id>/update/', views.update_user, name='update_user'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('products/', views.products, name='products'),
    path('products/<int:product_id>/approve/', views.approve_product, name='approve_product'),
    path('products/<int:product_id>/reject/', views.reject_product, name='reject_product'),
    path('orders/', views.orders, name='orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),  
    path('categories/', views.categories, name='categories'),
    path('categories/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path('categories/<int:category_id>/delete/', views.delete_category, name='delete_category'),
    path('reports/', views.reports, name='reports'),
    path('stock/', views.stock_overview, name='stock_overview'),
    path('stock/alerts/', views.stock_alerts, name='stock_alerts'),
    path('stock/history/', views.stock_history, name='stock_history'),
]
