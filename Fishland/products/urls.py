from django.urls import path
from . import views, seller_views

app_name = 'products'

urlpatterns = [
    # Customer-facing URLs
    path('', views.product_list, name='product_list'),
    path('<int:product_id>/', views.product_detail, name='product_detail'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/<int:category_id>/', views.category_detail, name='category_detail'),
    path('<int:product_id>/review/', views.add_review, name='add_review'),
    
    # Seller URLs
    path('seller/dashboard/', seller_views.seller_dashboard, name='seller_dashboard'),
    path('seller/stock/', seller_views.stock_management, name='stock_management'),
    path('seller/stock/<int:product_id>/update/', seller_views.update_stock, name='update_stock'),
    path('seller/stock/<int:product_id>/alerts/', seller_views.manage_stock_alerts, name='manage_stock_alerts'),
]
