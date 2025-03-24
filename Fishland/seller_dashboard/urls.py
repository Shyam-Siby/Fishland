from django.urls import path
from . import views

app_name = 'seller_dashboard'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Products
    path('products/', views.products, name='products'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('products/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    
    # Stock Management
    path('products/<int:product_id>/stock/', views.manage_stock, name='manage_stock'),
    path('products/<int:product_id>/stock/alert/', views.manage_stock_alert, name='manage_stock_alert'),
    
    # Orders
    path('orders/', views.orders, name='orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    
    # Analytics
    path('analytics/', views.analytics, name='analytics'),
    path('analytics/sales/', views.sales_analytics, name='sales_analytics'),
    path('analytics/stock/', views.stock_analytics, name='stock_analytics'),
]
