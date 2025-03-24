from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='category_images/', blank=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return self.name

class Product(models.Model):
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_order_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    stock_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.0)]
    )
    image = models.ImageField(upload_to='product_images/')
    is_available = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

    def update_stock(self, new_quantity, change_type, reason, user):
        """Update stock quantity and handle alerts."""
        print("\n=== Starting Stock Update in Model ===")
        print(f"Product: {self.name}")
        print(f"Previous Stock: {self.stock_quantity}kg")
        print(f"New Stock: {new_quantity}kg")
        print(f"Change Type: {change_type}")
        
        previous_quantity = self.stock_quantity
        self.stock_quantity = new_quantity
        self.save()
        
        print("Stock quantity updated in database")

        # Create stock history entry
        StockHistory.objects.create(
            product=self,
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            change_type=change_type,
            change_reason=reason,
            changed_by=user
        )
        print("Stock history entry created")

        # Check for low stock alert
        if hasattr(self, 'stock_alert'):
            print(f"\nChecking stock alert:")
            print(f"Has alert: Yes")
            print(f"Alert active: {self.stock_alert.is_active}")
            print(f"Alert threshold: {self.stock_alert.threshold_quantity}kg")
            print(f"Current stock: {new_quantity}kg")
            
            if self.stock_alert.is_active and new_quantity <= self.stock_alert.threshold_quantity:
                print("Stock is below threshold, sending alert...")
                self.notify_low_stock()
            else:
                print("No alert needed - either alert is inactive or stock is above threshold")
        else:
            print("\nNo stock alert set for this product")
            
        print("=== Stock Update in Model Complete ===\n")

    def notify_low_stock(self):
        """Send low stock alert email to seller."""
        from django.utils import timezone
        from django.core.mail import send_mail
        from django.conf import settings
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        from django.urls import reverse
        from django.contrib.sites.shortcuts import get_current_site
        from django.contrib.sites.models import Site
        import logging

        logger = logging.getLogger(__name__)
        
        try:
            # Debug print start
            print("\n=== Starting Low Stock Alert Process ===")
            print(f"Product ID: {self.id}")
            print(f"Product Name: {self.name}")
            print(f"Current Stock: {self.stock_quantity}kg")
            
            # Check if alert exists and is active
            if not hasattr(self, 'stock_alert'):
                print("No stock alert found for product")
                return
                
            alert = self.stock_alert
            if not alert.is_active:
                print("Stock alert exists but is not active")
                return
                
            print(f"Alert Threshold: {alert.threshold_quantity}kg")
            print(f"Alert Active: {alert.is_active}")
            print(f"Last Notification: {alert.last_notification_sent}")
            
            # Check notification cooldown
            if alert.last_notification_sent:
                time_since_last = timezone.now() - alert.last_notification_sent
                print(f"Hours since last notification: {time_since_last.total_seconds() / 3600:.2f}")
                if time_since_last.days < 1:
                    print("Skipping - Less than 24 hours since last notification")
                    return
            
            # Get site URL
            try:
                site = Site.objects.get_current()
                site_url = f"http://127.0.0.1:8000" if settings.DEBUG else f"https://{site.domain}"
                print(f"Site URL: {site_url}")
            except Exception as e:
                print(f"Error getting site URL: {str(e)}")
                site_url = "http://127.0.0.1:8000"
            
            # Prepare email context
            context = {
                'product': self,
                'site_url': site_url,
            }
            
            # Render email templates
            html_message = render_to_string('emails/low_stock_alert.html', context)
            plain_message = strip_tags(html_message)
            
            # Debug print email settings
            print("\nEmail Settings:")
            print(f"From: {settings.DEFAULT_FROM_EMAIL}")
            print(f"To: {self.seller.email}")
            print(f"Subject: Low Stock Alert: {self.name}")
            
            # Send email
            try:
                email_result = send_mail(
                    subject=f'Low Stock Alert: {self.name}',
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[self.seller.email],
                    html_message=html_message,
                    fail_silently=False
                )
                
                print(f"\nEmail send result: {email_result}")
                
                if email_result == 1:
                    # Update last notification time
                    alert.last_notification_sent = timezone.now()
                    alert.save()
                    print("Email sent successfully and notification time updated")
                else:
                    print("Failed to send email")
                
            except Exception as email_error:
                print(f"\nError sending email:")
                print(f"Error type: {type(email_error).__name__}")
                print(f"Error message: {str(email_error)}")
                raise
                
        except Exception as e:
            print(f"\nError in notify_low_stock:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            raise
            
        print("\n=== End Low Stock Alert Process ===")

    def check_stock_availability(self, requested_quantity):
        return self.stock_quantity >= requested_quantity and self.is_available

class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('product', 'user')
    
    def __str__(self):
        return f"{self.user.email}'s review on {self.product.name}"

class Promotion(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.discount_percentage}% off"

class StockHistory(models.Model):
    STOCK_CHANGE_TYPES = [
        ('ADDITION', 'Stock Added'),
        ('REDUCTION', 'Stock Reduced'),
        ('ADJUSTMENT', 'Stock Adjusted'),
        ('SALE', 'Stock Sold'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_history')
    previous_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    new_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    change_type = models.CharField(max_length=20, choices=STOCK_CHANGE_TYPES)
    change_reason = models.TextField()
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Stock Histories'

    def __str__(self):
        return f"{self.product.name} - {self.change_type} at {self.created_at}"

class StockAlert(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='stock_alert')
    threshold_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    last_notification_sent = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Alert for {self.product.name} at {self.threshold_quantity}kg"
