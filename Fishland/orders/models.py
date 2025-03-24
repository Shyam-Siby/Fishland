from django.db import models
from django.conf import settings
from products.models import Product
from django.utils import timezone

class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=50, default='Home')  # e.g., "Home", "Office"
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address_line1 = models.CharField(max_length=100)
    address_line2 = models.CharField(max_length=100, blank=True, null=True)  # Making it nullable
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=6)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.label} - {self.name}"

    def save(self, *args, **kwargs):
        if self.is_default:
            # Set all other addresses of this user to non-default
            Address.objects.filter(user=self.user).update(is_default=False)
        elif not Address.objects.filter(user=self.user).exists():
            # If this is the first address for the user, make it default
            self.is_default = True
        super().save(*args, **kwargs)

class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('ASSIGNED_TO_DELIVERY', 'Assigned to Delivery'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('ONLINE', 'Online Payment'),
    ]
    
    CANCELLATION_REASON_CHOICES = [
        ('OUT_OF_STOCK', 'Out of Stock'),
        ('PRICE_MISMATCH', 'Price Mismatch'),
        ('QUALITY_ISSUES', 'Quality Issues'),
        ('DELIVERY_ISSUES', 'Cannot Deliver to Location'),
        ('OTHER', 'Other'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    delivery_boy = models.ForeignKey('delivery.DeliveryProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_orders')
    delivery_rating = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])
    delivery_feedback = models.TextField(null=True, blank=True)
    order_number = models.CharField(max_length=20, unique=True)
    delivery_address = models.ForeignKey(
        Address, 
        on_delete=models.PROTECT, 
        related_name='orders',
        null=True,  # Allow null for existing records
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='COD')
    
    # Razorpay fields
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    delivery_date = models.DateField()
    delivery_time = models.CharField(max_length=10)  # Store as HH:MM format
    
    delivery_assigned_at = models.DateTimeField(null=True, blank=True)
    delivery_pickup_at = models.DateTimeField(null=True, blank=True)
    delivery_completed_at = models.DateTimeField(null=True, blank=True)
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    delivery_feedback = models.TextField(null=True, blank=True)
    delivery_rating = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])
    
    cancellation_reason = models.CharField(max_length=20, choices=CANCELLATION_REASON_CHOICES, null=True, blank=True)
    cancellation_note = models.TextField(blank=True, null=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    processing_at = models.DateTimeField(null=True, blank=True)
    out_for_delivery_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order #{self.order_number}"

    @property
    def has_review(self):
        return hasattr(self, 'review')

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number: ORD + YYYYMMDD + 4 random digits
            now = timezone.now()
            date_str = now.strftime('%Y%m%d')
            last_order = Order.objects.filter(
                order_number__startswith=f'ORD{date_str}'
            ).order_by('-order_number').first()
            
            if last_order:
                last_number = int(last_order.order_number[-4:])
                new_number = str(last_number + 1).zfill(4)
            else:
                new_number = '0001'
            
            self.order_number = f'ORD{date_str}{new_number}'
        
        # Update timestamps based on status changes
        if self.status == 'CONFIRMED' and not self.confirmed_at:
            self.confirmed_at = timezone.now()
        elif self.status == 'PROCESSING' and not self.processing_at:
            self.processing_at = timezone.now()
        elif self.status == 'ASSIGNED_TO_DELIVERY' and not self.delivery_assigned_at:
            self.delivery_assigned_at = timezone.now()
        elif self.status == 'OUT_FOR_DELIVERY' and not self.out_for_delivery_at:
            self.out_for_delivery_at = timezone.now()
        elif self.status == 'DELIVERED' and not self.delivered_at:
            self.delivered_at = timezone.now()
        elif self.status == 'CANCELLED' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        
        super().save(*args, **kwargs)

    def notify_delivery_assignment(self):
        """Send email notification to delivery agent about new order assignment."""
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        from django.conf import settings
        from django.contrib.sites.models import Site
        import logging

        logger = logging.getLogger(__name__)
        
        try:
            print("\n=== Starting Delivery Assignment Notification ===")
            print(f"Order: #{self.id}")
            print(f"Delivery Agent: {self.delivery_boy}")
            
            if not self.delivery_boy:
                print("No delivery agent assigned")
                return
                
            # Get site URL for the email template
            try:
                site = Site.objects.get_current()
                site_url = f"http://127.0.0.1:8000" if settings.DEBUG else f"https://{site.domain}"
                print(f"Site URL: {site_url}")
            except Exception as e:
                print(f"Error getting site URL: {str(e)}")
                site_url = "http://127.0.0.1:8000"
            
            # Prepare email context
            context = {
                'order': self,
                'site_url': site_url,
            }
            
            # Render email templates
            html_message = render_to_string('emails/delivery_assignment.html', context)
            plain_message = strip_tags(html_message)
            
            # Debug print email settings
            print("\nEmail Settings:")
            print(f"From: {settings.DEFAULT_FROM_EMAIL}")
            print(f"To: {self.delivery_boy.user.email}")
            print(f"Subject: New Delivery Assignment - Order #{self.order_number}")
            
            # Send email
            email_result = send_mail(
                subject=f'New Delivery Assignment - Order #{self.order_number}',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.delivery_boy.user.email],
                html_message=html_message,
                fail_silently=False
            )
            
            print(f"\nEmail send result: {email_result}")
            if email_result == 1:
                print("Email sent successfully")
            else:
                print("Failed to send email")
                
        except Exception as e:
            print(f"\nError in notify_delivery_assignment:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            logger.error(f"Failed to send delivery assignment notification for Order #{self.id}: {str(e)}")
            
        print("=== End Delivery Assignment Notification ===\n")

    class Meta:
        ordering = ['-created_at']

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)  # Changed to DecimalField for kg
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity}kg of {self.product.name} in Order #{self.order.order_number}"

class OrderReview(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='review')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='order_reviews')
    rating = models.PositiveIntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review for {self.order}"

    class Meta:
        ordering = ['-created_at']
