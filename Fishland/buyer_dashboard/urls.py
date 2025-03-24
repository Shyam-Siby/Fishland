from django.urls import path
from . import views

app_name = 'buyer_dashboard'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Product Views
    path('products/', views.product_list, name='product_list'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('products/category/<int:category_id>/', views.category_products, name='category_products'),
    path('products/search/', views.search_products, name='search_products'),
    
    # Saved Products
    path('saved-products/', views.saved_products, name='saved_products'),
    path('products/<int:product_id>/save/', views.save_product, name='save_product'),
    path('products/<int:product_id>/unsave/', views.unsave_product, name='unsave_product'),
    
    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('products/<int:product_id>/notify/', views.set_notification, name='set_notification'),
    path('notifications/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),
    
    # Orders
    path('orders/', views.order_history, name='order_history'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    
    # Quick Order
    path('products/<int:product_id>/quick-order/', views.quick_order, name='quick_order'),
]
