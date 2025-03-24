from django.urls import path
from . import views

app_name = 'buyer'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),
    path('orders/<str:order_number>/review/', views.order_review, name='order_review'),
    path('orders/<str:order_number>/review/edit/', views.edit_review, name='edit_review'),
    path('addresses/', views.addresses, name='addresses'),
    path('addresses/add/', views.add_address, name='add_address'),
    path('addresses/<int:address_id>/edit/', views.edit_address, name='edit_address'),
    path('addresses/<int:address_id>/delete/', views.delete_address, name='delete_address'),
    path('addresses/<int:address_id>/make-default/', views.make_default_address, name='make_default_address'),
    path('orders/<str:order_number>/cancel/', views.cancel_order, name='cancel_order'),
]
