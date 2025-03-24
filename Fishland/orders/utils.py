from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.sites.models import Site

def send_order_confirmation_email(order):
    """Send order confirmation email to customer."""
    subject = f'Order Confirmation - FISHLAND Order #{order.order_number}'
    
    # Get site URL
    try:
        site = Site.objects.get_current()
        site_url = f'https://{site.domain}'
    except Site.DoesNotExist:
        site_url = 'http://localhost:8000'
    
    # Render HTML email template
    html_message = render_to_string('email/order_confirmation.html', {
        'order': order,
        'site_name': 'FISHLAND',
        'site_url': site_url,
        'support_email': settings.DEFAULT_FROM_EMAIL,
    })
    
    # Create plain text version by stripping HTML
    plain_message = strip_tags(html_message)
    
    # Send email
    send_mail(
        subject=subject,
        message=plain_message,
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.user.email],
        fail_silently=False,
    )

def send_order_status_update_email(order):
    """Send order status update email to customer."""
    subject = f'Order Status Update - FISHLAND Order #{order.order_number}'
    
    # Get site URL
    try:
        site = Site.objects.get_current()
        site_url = f'https://{site.domain}'
    except Site.DoesNotExist:
        site_url = 'http://localhost:8000'
    
    # Render HTML email template
    html_message = render_to_string('email/order_status_update.html', {
        'order': order,
        'site_name': 'FISHLAND',
        'site_url': site_url,
        'support_email': settings.DEFAULT_FROM_EMAIL,
    })
    
    # Create plain text version by stripping HTML
    plain_message = strip_tags(html_message)
    
    # Send email
    send_mail(
        subject=subject,
        message=plain_message,
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.user.email],
        fail_silently=False,
    )
