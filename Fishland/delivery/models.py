from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator

# Create your models here.

class DeliveryProfile(models.Model):
    VEHICLE_TYPES = [
        ('BIKE', 'Motorcycle/Scooter'),
        ('BICYCLE', 'Bicycle'),
        ('CAR', 'Car'),
        ('VAN', 'Van'),
    ]

    STATUS_CHOICES = [
        ('ONLINE', 'Online'),
        ('OFFLINE', 'Offline'),
        ('BUSY', 'Busy'),
        ('ON_DELIVERY', 'On Delivery'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_profile')
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_TYPES, default='BIKE')
    vehicle_number = models.CharField(max_length=15, default='')
    license_number = models.CharField(max_length=20, default='')
    current_location = models.CharField(max_length=200, blank=True, default='')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='OFFLINE')
    is_verified = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    total_deliveries = models.IntegerField(default=0)
    successful_deliveries = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_status_change = models.DateTimeField(auto_now=True)
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    phone = models.CharField(max_length=15, default='')
    license_image = models.ImageField(upload_to='delivery_documents/licenses/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_status_display()}"

    @property
    def is_available(self):
        return self.status == 'ONLINE'

    @property
    def is_busy(self):
        return self.status in ['BUSY', 'ON_DELIVERY']

    @property
    def is_on_break(self):
        return self.status == 'BREAK'

    @property
    def is_offline(self):
        return self.status == 'OFFLINE'

    @property
    def success_rate(self):
        if self.total_deliveries > 0:
            return (self.successful_deliveries / self.total_deliveries) * 100
        return 0

    @property
    def assigned_orders(self):
        return self.order_set.filter(status__in=['ASSIGNED_TO_DELIVERY', 'OUT_FOR_DELIVERY'])

    @property
    def average_rating(self):
        if self.total_deliveries > 0:
            return self.rating / self.total_deliveries
        return None


class DeliveryFee(models.Model):
    base_fee = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)
    per_km_fee = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    min_distance = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    max_distance = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    free_delivery_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Delivery Fee'
        verbose_name_plural = 'Delivery Fees'

    def __str__(self):
        return f"Delivery Fee (Base: ₹{self.base_fee}, Per KM: ₹{self.per_km_fee})"

    @classmethod
    def get_active_fee(cls):
        return cls.objects.filter(is_active=True).first()

    def calculate_fee(self, distance_km, order_total):
        """
        Calculate delivery fee based on distance and order total
        """
        if order_total >= self.free_delivery_threshold:
            return 0

        if distance_km < self.min_distance:
            distance_km = self.min_distance
        elif distance_km > self.max_distance:
            distance_km = self.max_distance

        total_fee = self.base_fee + (distance_km * self.per_km_fee)
        return total_fee
