from django.contrib import admin
from django.contrib import messages
from .models import DeliveryProfile

class DeliveryProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_full_name', 'phone', 'vehicle_type', 'status', 'is_verified', 'is_active', 'rating']
    list_filter = ['status', 'is_verified', 'is_active', 'vehicle_type']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'phone']
    readonly_fields = ['created_at', 'updated_at', 'last_status_change']
    actions = ['verify_selected_agents', 'reject_selected_agents']

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Full Name'

    def verify_selected_agents(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(
            request,
            f'{updated} delivery agents have been verified successfully.',
            messages.SUCCESS
        )
    verify_selected_agents.short_description = 'Verify selected delivery agents'

    def reject_selected_agents(self, request, queryset):
        updated = queryset.update(is_verified=False, is_active=False)
        self.message_user(
            request,
            f'{updated} delivery agents have been rejected.',
            messages.WARNING
        )
    reject_selected_agents.short_description = 'Reject selected delivery agents'

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'phone')
        }),
        ('Vehicle Information', {
            'fields': ('vehicle_type', 'vehicle_number', 'license_number', 'license_image')
        }),
        ('Status & Verification', {
            'fields': ('status', 'is_verified', 'is_active')
        }),
        ('Performance', {
            'fields': ('rating', 'total_deliveries', 'successful_deliveries')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_status_change'),
            'classes': ('collapse',)
        })
    )

# Explicitly register the model with the admin site
admin.site.register(DeliveryProfile, DeliveryProfileAdmin) 