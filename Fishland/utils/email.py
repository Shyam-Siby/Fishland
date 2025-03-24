from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

def send_templated_email(template_name, context, subject, recipient_list):
    """
    Send an HTML email using a template
    """
    html_content = render_to_string(f'email/{template_name}.html', context)
    text_content = strip_tags(html_content)
    
    msg = EmailMultiAlternatives(
        subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        recipient_list
    )
    msg.attach_alternative(html_content, "text/html")
    return msg.send()

def send_order_confirmation(order):
    """
    Send order confirmation email
    """
    context = {
        'order': order,
        'user': order.user,
        'items': order.order_items.all(),
    }
    return send_templated_email(
        'order_confirmation',
        context,
        f'Order Confirmation - #{order.order_number}',
        [order.user.email]
    )

def send_order_status_update(order):
    """
    Send order status update email
    """
    context = {
        'order': order,
        'user': order.user,
        'status': order.get_status_display(),
    }
    return send_templated_email(
        'order_status_update',
        context,
        f'Order Status Update - #{order.order_number}',
        [order.user.email]
    )

def send_welcome_email(user):
    """
    Send welcome email to new users
    """
    context = {
        'user': user,
        'site_name': 'FISHLAND',
    }
    return send_templated_email(
        'welcome',
        context,
        'Welcome to FISHLAND!',
        [user.email]
    )

def send_password_reset_email(user, reset_url):
    """
    Send password reset email
    """
    context = {
        'user': user,
        'reset_url': reset_url,
        'site_name': 'FISHLAND',
    }
    return send_templated_email(
        'password_reset',
        context,
        'Reset Your FISHLAND Password',
        [user.email]
    )

def send_seller_approval_email(user):
    """
    Send seller approval notification
    """
    context = {
        'user': user,
        'site_name': 'FISHLAND',
    }
    return send_templated_email(
        'seller_approval',
        context,
        'Your FISHLAND Seller Account is Approved!',
        [user.email]
    )
