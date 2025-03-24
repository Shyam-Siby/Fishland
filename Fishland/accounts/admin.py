from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, SellerProfile, BuyerProfile

class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'role', 'is_verified', 'is_staff')
    list_filter = ('role', 'is_verified', 'is_staff')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username', 'first_name', 'last_name', 'phone_number')}),
        ('Business info', {'fields': ('role', 'company_name', 'address', 'gst_number')}),
        ('Permissions', {'fields': ('is_verified', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )
    search_fields = ('email', 'username', 'company_name')
    ordering = ('email',)

class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'rating', 'total_ratings')
    search_fields = ('user__email', 'user__company_name')

class BuyerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'business_type')
    search_fields = ('user__email', 'user__company_name')

admin.site.register(User, CustomUserAdmin)
admin.site.register(SellerProfile, SellerProfileAdmin)
admin.site.register(BuyerProfile, BuyerProfileAdmin)
