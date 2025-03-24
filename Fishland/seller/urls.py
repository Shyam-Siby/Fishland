from django.urls import path
from . import views

app_name = 'seller'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/confirm/', views.confirm_order, name='confirm_order'),
    path('orders/<int:order_id>/process/', views.process_order, name='process_order'),
    path('orders/<int:order_id>/assign-delivery/', views.assign_delivery, name='assign_delivery'),
    path('orders/<int:order_id>/start-delivery/', views.start_delivery, name='start_delivery'),
    path('orders/<int:order_id>/unassign-delivery/', views.unassign_delivery, name='unassign_delivery'),
    path('orders/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('orders/<int:order_id>/ship/', views.ship_order, name='ship_order'),
    path('orders/<int:order_id>/deliver/', views.deliver_order, name='deliver_order'),
    path('products/', views.product_list, name='products'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('products/<int:product_id>/toggle/', views.toggle_product, name='toggle_product'),
    path('analytics/', views.analytics, name='analytics'),
    path('reports/<str:report_type>/', views.download_report, name='download_report'),
    path('profile/', views.profile, name='profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('profile/upload-picture/', views.upload_profile_picture, name='upload_profile_picture'),
    path('settings/', views.seller_settings, name='settings'),
    path('settings/notifications/', views.update_notification_settings, name='update_notifications'),
    path('settings/payment/', views.update_payment_settings, name='update_payment'),
    path('settings/shipping/', views.update_shipping_settings, name='update_shipping'),
    path('settings/tax/', views.update_tax_settings, name='update_tax'),
    path('settings/privacy/', views.update_privacy_settings, name='update_privacy'),
    
    # Stock Management URLs
    path('stock/', views.stock_management, name='stock_management'),
    path('stock/<int:product_id>/update/', views.update_stock, name='update_stock'),
    path('stock/<int:product_id>/alert/', views.set_stock_alert, name='set_stock_alert'),
]
