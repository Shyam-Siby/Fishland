from django.db import models
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

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

    def verify_agent(self):
        """Verify a delivery agent after document verification."""
        self.is_verified = True
        self.save()
        self.send_verification_notification()

    def send_verification_notification(self):
        """Send email notification to delivery agent about verification status."""
        subject = 'Your Delivery Agent Account has been Verified'
        html_message = render_to_string('delivery/email/verification_success.html', {
            'name': self.user.get_full_name(),
        })
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send verification email: {str(e)}")

    @property
    def is_available(self):
        return self.status == 'ONLINE'

    @property
    def is_busy(self):
        return self.status in ['BUSY', 'ON_DELIVERY']

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