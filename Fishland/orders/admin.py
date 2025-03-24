from django.contrib import admin
from .models import Order, OrderItem, Address, OrderReview

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['total']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'status', 'total', 'created_at']
    list_filter = ['status', 'payment_status', 'payment_method', 'created_at']
    search_fields = ['order_number', 'user__email', 'delivery_address__name']
    readonly_fields = ['order_number', 'subtotal', 'delivery_fee', 'total', 'created_at', 
                      'confirmed_at', 'processing_at', 'out_for_delivery_at', 
                      'delivered_at', 'cancelled_at']
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ['user']
        return self.readonly_fields

@admin.register(OrderReview)
class OrderReviewAdmin(admin.ModelAdmin):
    list_display = ['order', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['order__order_number', 'user__email', 'comment']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'label', 'name', 'city', 'is_default']
    list_filter = ['is_default', 'city', 'state']
    search_fields = ['user__email', 'name', 'phone', 'address_line1', 'city']
    readonly_fields = ['created_at', 'updated_at']
