from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from utils.media import get_profile_image_path

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        SELLER = 'SELLER', 'Seller'
        BUYER = 'BUYER', 'Buyer'
        DELIVERY_BOY = 'DELIVERY_BOY', 'Delivery Boy'
    
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(max_length=15, choices=Role.choices, default=Role.BUYER)
    phone = PhoneNumberField(blank=True)  # Renamed from phone_number
    profile_picture = models.ImageField(upload_to=get_profile_image_path, blank=True, null=True)
    company_name = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    gst_number = models.CharField(max_length=15, blank=True)
    is_verified = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    @property
    def is_seller(self):
        return self.role == self.Role.SELLER

    @property
    def is_buyer(self):
        return self.role == self.Role.BUYER

    @property
    def is_delivery_boy(self):
        return self.role == self.Role.DELIVERY_BOY

    @property
    def profile_picture_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return None

class SellerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    business_name = models.CharField(max_length=100, blank=True)
    business_description = models.TextField(blank=True)
    gst_number = models.CharField(max_length=15, blank=True)
    business_license_number = models.CharField(max_length=50, blank=True)
    business_license = models.FileField(upload_to='seller_documents/', blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    bank_ifsc = models.CharField(max_length=20, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    total_ratings = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.email}'s Seller Profile"

class BuyerProfile(models.Model):
    BUSINESS_TYPES = [
        ('RETAILER', 'Retailer'),
        ('WHOLESALER', 'Wholesaler'),
        ('RESTAURANT', 'Restaurant'),
        ('HOTEL', 'Hotel'),
        ('OTHER', 'Other'),
    ]
    
    PAYMENT_METHODS = [
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('UPI', 'UPI'),
        ('CREDIT_CARD', 'Credit Card'),
        ('COD', 'Cash on Delivery'),
        ('OTHER', 'Other'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer_profile')
    business_type = models.CharField(max_length=50, choices=BUSINESS_TYPES, default='OTHER')
    preferred_payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS, default='BANK_TRANSFER')
    shipping_address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    
    def __str__(self):
        return f"{self.user.email}'s Buyer Profile"
