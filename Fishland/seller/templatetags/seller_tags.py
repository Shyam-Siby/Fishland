from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def order_status_class(status):
    status_classes = {
        'PENDING': 'bg-warning',
        'CONFIRMED': 'bg-info',
        'READY_FOR_DELIVERY': 'bg-primary',
        'ASSIGNED_TO_DELIVERY': 'bg-info',
        'OUT_FOR_DELIVERY': 'bg-info',
        'DELIVERED': 'bg-success',
        'CANCELLED': 'bg-danger'
    }
    return status_classes.get(status, 'bg-secondary')

@register.simple_tag
def order_status_badge(status):
    status_display = {
        'PENDING': 'Pending',
        'CONFIRMED': 'Confirmed',
        'READY_FOR_DELIVERY': 'Ready for Delivery',
        'ASSIGNED_TO_DELIVERY': 'Assigned to Delivery',
        'OUT_FOR_DELIVERY': 'Out for Delivery',
        'DELIVERED': 'Delivered',
        'CANCELLED': 'Cancelled'
    }
    status_class = order_status_class(status)
    display_text = status_display.get(status, status)
    return mark_safe(f'<span class="badge {status_class}">{display_text}</span>')
