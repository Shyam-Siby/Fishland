from django.db import models
from django.conf import settings
from products.models import Product
from django.core.validators import MinValueValidator
from decimal import Decimal

# Create your models here.

class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.email}"

    @property
    def total(self):
        return sum(item.total for item in self.items.all())

    @property
    def item_count(self):
        return self.items.count()

    def clear(self):
        self.items.all().delete()

    def has_stock_issues(self):
        for item in self.items.all():
            if item.quantity > item.product.stock_quantity:
                return True
        return False

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity}kg of {self.product.name}"

    @property
    def total(self):
        return self.quantity * self.product.price_per_kg

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.quantity < self.product.minimum_order_quantity:
            raise ValidationError({
                'quantity': f'Minimum order quantity is {self.product.minimum_order_quantity}kg'
            })
        if self.quantity > self.product.stock_quantity:
            raise ValidationError({
                'quantity': f'Only {self.product.stock_quantity}kg available in stock'
            })
