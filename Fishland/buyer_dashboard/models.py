from django.db import models
from django.conf import settings
from products.models import Product
from decimal import Decimal

class SavedProduct(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.email} - {self.product.name}"

class ProductNotification(models.Model):
    NOTIFICATION_TYPES = [
        ('STOCK', 'Back in Stock'),
        ('PRICE', 'Price Drop'),
        ('PROMO', 'Promotion'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    is_active = models.BooleanField(default=True)
    target_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Target price for price drop notification"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'product', 'notification_type')

    def __str__(self):
        return f"{self.user.email} - {self.product.name} ({self.get_notification_type_display()})"
