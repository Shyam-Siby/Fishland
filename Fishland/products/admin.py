from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, ProductReview, Promotion, StockHistory, StockAlert

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'seller', 'category', 'price_per_kg', 'stock_quantity', 
                   'stock_status', 'is_available', 'is_approved')
    list_filter = ('category', 'is_available', 'is_approved')
    search_fields = ('name', 'seller__email', 'category__name')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['approve_products', 'disapprove_products']

    def stock_status(self, obj):
        if hasattr(obj, 'stock_alert') and obj.stock_alert.is_active:
            if obj.stock_quantity <= obj.stock_alert.threshold_quantity:
                return format_html(
                    '<span style="color: red;">Low Stock ({} kg)</span>',
                    obj.stock_quantity
                )
        if obj.stock_quantity <= 0:
            return format_html(
                '<span style="color: red;">Out of Stock</span>'
            )
        return format_html(
            '<span style="color: green;">In Stock ({} kg)</span>',
            obj.stock_quantity
        )
    
    stock_status.short_description = 'Stock Status'

    def approve_products(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f"{queryset.count()} products were approved.")
    
    def disapprove_products(self, request, queryset):
        queryset.update(is_approved=False)
        self.message_user(request, f"{queryset.count()} products were disapproved.")

@admin.register(StockHistory)
class StockHistoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'previous_quantity', 'new_quantity', 'change_type', 
                   'changed_by', 'created_at')
    list_filter = ('change_type', 'created_at')
    search_fields = ('product__name', 'changed_by__email', 'change_reason')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ('product', 'threshold_quantity', 'is_active', 
                   'last_notification_sent')
    list_filter = ('is_active',)
    search_fields = ('product__name',)
    readonly_fields = ('last_notification_sent', 'created_at', 'updated_at')

# Register existing models
admin.site.register(Category)
admin.site.register(ProductReview)
admin.site.register(Promotion)
