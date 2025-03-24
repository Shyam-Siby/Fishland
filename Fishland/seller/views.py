from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q, F, Avg, FloatField, Case, When, ExpressionWrapper, Value
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from products.models import Product, Category
from orders.models import Order, OrderItem
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from products.models import StockHistory, StockAlert
from delivery.models import DeliveryProfile
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings as django_settings
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import update_session_auth_hash

# Create your views here.

@login_required
def dashboard(request):
    """Seller dashboard view."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to access the seller dashboard.")
        return redirect('shop:home')
    
    # Get seller's products with select_related for optimization
    products = Product.objects.filter(seller=request.user).select_related('category')
    
    # Product statistics
    active_products = products.filter(is_available=True).count()
    total_products = products.count()
    pending_products = products.filter(is_approved=False).count()
    
    # Stock statistics with annotations
    stock_stats = products.aggregate(
        low_stock=Count('id', filter=Q(stock_quantity__lte=F('stock_alert'))),
        out_of_stock=Count('id', filter=Q(stock_quantity=0))
    )
    low_stock_products = stock_stats['low_stock']
    out_of_stock_products = stock_stats['out_of_stock']
    
    # Order statistics with optimized queries
    today = timezone.now().date()
    order_items = OrderItem.objects.filter(
        product__seller=request.user
    ).select_related('order', 'product')
    
    # Use aggregation for better performance
    order_stats = order_items.aggregate(
        orders_today=Count('order', filter=Q(order__created_at__date=today), distinct=True),
        total_orders=Count('order', distinct=True),
        revenue_today=Sum(
            'total',
            filter=Q(order__created_at__date=today, order__status='DELIVERED')
        ),
        total_revenue=Sum('total', filter=Q(order__status='DELIVERED'))
    )
    
    orders_today = order_stats['orders_today']
    total_orders = order_stats['total_orders']
    revenue_today = order_stats['revenue_today'] or 0
    total_revenue = order_stats['total_revenue'] or 0
    
    # Get recent orders with related data
    recent_orders = Order.objects.filter(
        order_items__product__seller=request.user
    ).distinct().select_related(
        'user',
        'delivery_boy',
        'delivery_boy__user'
    ).prefetch_related(
        'order_items',
        'order_items__product'
    ).order_by('-created_at')[:5]
    
    # Get low stock products for alerts
    low_stock_items = products.filter(
        stock_quantity__lte=F('stock_alert')
    ).order_by('stock_quantity')[:5]
    
    context = {
        'active_products': active_products,
        'total_products': total_products,
        'pending_products': pending_products,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'orders_today': orders_today,
        'total_orders': total_orders,
        'revenue_today': revenue_today,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'low_stock_items': low_stock_items,
    }
    
    return render(request, 'seller/dashboard.html', context)

@login_required
def product_list(request):
    """List seller's products."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to access the seller products.")
        return redirect('shop:home')
    
    # Get filter parameters
    category_id = request.GET.get('category')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    # Base queryset
    products = Product.objects.filter(seller=request.user)
    
    # Apply filters
    if category_id:
        products = products.filter(category_id=category_id)
    
    if status:
        if status == 'active':
            products = products.filter(is_available=True, is_approved=True)
        elif status == 'pending':
            products = products.filter(is_approved=False)
        elif status == 'unavailable':
            products = products.filter(is_available=False)
    
    if search:
        products = products.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search)
        )
    
    # Get all categories for the filter dropdown
    categories = Category.objects.all()
    
    context = {
        'title': 'My Products',
        'products': products,
        'categories': categories,
    }
    return render(request, 'seller/products.html', context)

@login_required
def order_list(request):
    """List all orders for the seller with filtering and pagination."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to access the seller dashboard.")
        return redirect('shop:home')
    
    # Get status filter
    status = request.GET.get('status', 'all')
    needs_delivery = request.GET.get('needs_delivery') == 'true'
    
    # Base queryset with optimized joins
    orders = Order.objects.filter(
        order_items__product__seller=request.user
    ).distinct().select_related(
        'user',
        'delivery_boy',
        'delivery_boy__user',
        'delivery_address'
    ).prefetch_related(
        'order_items',
        'order_items__product'
    )
    
    # Apply filters
    if status != 'all':
        orders = orders.filter(status=status)
    
    if needs_delivery:
        orders = orders.filter(
            status='READY_FOR_DELIVERY',
            delivery_boy__isnull=True
        )
    
    # Order by most recent first
    orders = orders.order_by('-created_at')
    
    # Get delivery statistics
    delivery_stats = {
        'ready_for_delivery': orders.filter(status='READY_FOR_DELIVERY', delivery_boy__isnull=True).count(),
        'assigned': orders.filter(status='ASSIGNED_TO_DELIVERY').count(),
        'out_for_delivery': orders.filter(status='OUT_FOR_DELIVERY').count(),
        'delivered_today': orders.filter(
            status='DELIVERED',
            delivery_completed_at__date=timezone.now().date()
        ).count()
    }
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(orders, 10)
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)
    
    context = {
        'orders': orders,
        'status': status,
        'delivery_stats': delivery_stats,
        'needs_delivery': needs_delivery
    }
    
    return render(request, 'seller/order_list.html', context)

@login_required
def start_delivery(request, order_id):
    """Start delivery for an order that has been assigned to a delivery agent."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('shop:home')
    
    order = get_object_or_404(Order, id=order_id)
    
    # Verify the order belongs to this seller
    if not order.order_items.filter(product__seller=request.user).exists():
        messages.error(request, "You don't have permission to manage this order.")
        return redirect('seller:order_list')
    
    # Verify order is in correct state
    if order.status != 'ASSIGNED_TO_DELIVERY':
        messages.error(request, "This order cannot be started for delivery at this time.")
        return redirect('seller:order_detail', order_id=order.id)
    
    # Verify delivery agent is assigned
    if not order.delivery_boy:
        messages.error(request, "No delivery agent is assigned to this order.")
        return redirect('seller:order_detail', order_id=order.id)
    
    # Update order status
    order.status = 'OUT_FOR_DELIVERY'
    order.save()
    
    messages.success(request, f"Order #{order.id} is now out for delivery.")
    return redirect('seller:order_detail', order_id=order.id)

@login_required
def unassign_delivery(request, order_id):
    """Remove assigned delivery agent from an order."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('shop:home')
    
    order = get_object_or_404(Order, id=order_id)
    
    # Verify the order belongs to this seller
    if not order.order_items.filter(product__seller=request.user).exists():
        messages.error(request, "You don't have permission to manage this order.")
        return redirect('seller:order_list')
    
    # Verify order is in correct state
    if order.status != 'ASSIGNED_TO_DELIVERY':
        messages.error(request, "Delivery agent can only be unassigned when order is in 'Assigned to Delivery' state.")
        return redirect('seller:order_detail', order_id=order.id)
    
    # Remove delivery agent
    order.delivery_boy = None
    order.status = 'READY_FOR_DELIVERY'
    order.save()
    
    messages.success(request, f"Delivery agent has been unassigned from order #{order.id}.")
    return redirect('seller:order_list')

@login_required
def confirm_order(request, order_id):
    """Confirm a pending order."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('shop:home')
    
    order = get_object_or_404(Order, id=order_id)
    
    # Verify the order belongs to products sold by this seller
    if not order.order_items.filter(product__seller=request.user).exists():
        messages.error(request, "You don't have permission to manage this order.")
        return redirect('seller:order_list')
    
    if request.method == 'POST':
        if order.status == 'PENDING':
            order.status = 'CONFIRMED'
            order.save()
            messages.success(request, f'Order #{order.id} has been confirmed.')
        else:
            messages.error(request, 'Order cannot be confirmed in its current status.')
    
    return redirect('seller:order_list')

@login_required
def process_order(request, order_id):
    """Mark order as ready for delivery."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('shop:home')
    
    order = get_object_or_404(Order, id=order_id)
    
    # Verify the order belongs to products sold by this seller
    if not order.order_items.filter(product__seller=request.user).exists():
        messages.error(request, "You don't have permission to manage this order.")
        return redirect('seller:order_list')
    
    if request.method == 'POST':
        if order.status == 'CONFIRMED':
            order.status = 'READY_FOR_DELIVERY'
            order.save()
            messages.success(request, f'Order #{order.id} is ready for delivery.')
        else:
            messages.error(request, 'Order cannot be processed in its current status.')
    
    return redirect('seller:order_list')

@login_required
def ship_order(request, order_id):
    """Mark order as shipped."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to ship orders.")
        return redirect('shop:home')
    
    order = get_object_or_404(Order, id=order_id)
    
    # Check if any of the order items belong to this seller
    if not order.order_items.filter(product__seller=request.user).exists():
        messages.error(request, "You don't have permission to ship this order.")
        return redirect('seller:orders')
    
    # Check if order is in correct status
    if order.status != 'PROCESSING':
        messages.error(request, "This order cannot be shipped at this time.")
        return redirect('seller:orders')
    
    # Update order status
    order.status = 'SHIPPED'
    order.save()
    
    messages.success(request, f"Order #{order.order_number} has been marked as shipped.")
    return redirect('seller:orders')

@login_required
def deliver_order(request, order_id):
    """Mark order as delivered."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to mark orders as delivered.")
        return redirect('shop:home')
    
    order = get_object_or_404(Order, id=order_id)
    
    # Check if any of the order items belong to this seller
    if not order.order_items.filter(product__seller=request.user).exists():
        messages.error(request, "You don't have permission to mark this order as delivered.")
        return redirect('seller:orders')
    
    # Check if order is in correct status
    if order.status != 'SHIPPED':
        messages.error(request, "This order cannot be marked as delivered at this time.")
        return redirect('seller:orders')
    
    # Update order status
    order.status = 'DELIVERED'
    order.save()
    
    messages.success(request, f"Order #{order.order_number} has been marked as delivered.")
    return redirect('seller:orders')

@login_required
def cancel_order(request, order_id):
    """Cancel an order with reason and send email notification to customer."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to cancel orders.")
        return redirect('shop:home')
    
    order = get_object_or_404(Order, id=order_id)
    
    # Check if order belongs to the seller
    if not order.order_items.filter(product__seller=request.user).exists():
        messages.error(request, "You don't have permission to cancel this order.")
        return redirect('seller:order_list')
    
    # Check if order can be cancelled
    if order.status in ['DELIVERED', 'CANCELLED']:
        messages.error(request, f"Cannot cancel order in {order.get_status_display()} status.")
        return redirect('seller:order_detail', order_id=order.id)
    
    if request.method == 'POST':
        cancellation_reason = request.POST.get('cancellation_reason')
        cancellation_note = request.POST.get('cancellation_note')
        
        if not cancellation_reason:
            messages.error(request, "Please select a cancellation reason.")
            return redirect('seller:cancel_order', order_id=order.id)
        
        try:
            # If order was assigned to delivery, update their status
            if order.delivery_boy:
                order.delivery_boy = None
                order.delivery_assigned_at = None
            
            # Update order status
            order.status = 'CANCELLED'
            order.cancellation_reason = cancellation_reason
            order.cancellation_note = cancellation_note
            order.cancelled_at = timezone.now()
            
            # If payment was made, mark for refund
            if order.payment_status == 'PAID':
                order.payment_status = 'REFUNDED'
            
            order.save()
            
            # Debug print order details
            print("\nOrder Details:")
            print(f"Order ID: {order.id}")
            print(f"Order Number: {order.order_number}")
            print(f"Customer Email: {order.user.email}")
            print(f"Cancellation Reason: {order.get_cancellation_reason_display()}")
            
            # Prepare email context
            context = {
                'order': order,
                'customer_name': order.user.get_full_name() or order.user.email,
                'order_number': order.order_number,
                'cancellation_reason': order.get_cancellation_reason_display(),
                'cancellation_note': cancellation_note,
                'seller_name': request.user.get_full_name() or request.user.email,
            }
            
            try:
                # Debug print email settings
                print("\nEmail Settings:")
                print(f"EMAIL_BACKEND: {django_settings.EMAIL_BACKEND}")
                print(f"EMAIL_HOST: {django_settings.EMAIL_HOST}")
                print(f"EMAIL_PORT: {django_settings.EMAIL_PORT}")
                print(f"EMAIL_USE_TLS: {django_settings.EMAIL_USE_TLS}")
                print(f"EMAIL_HOST_USER: {django_settings.EMAIL_HOST_USER}")
                print(f"DEFAULT_FROM_EMAIL: {django_settings.DEFAULT_FROM_EMAIL}")
                
                # Render email templates
                html_message = render_to_string('emails/order_cancelled.html', context)
                plain_message = strip_tags(html_message)
                
                # Debug print message
                print("\nEmail Content:")
                print(f"Subject: Order #{order.order_number} Cancelled")
                print(f"From: {django_settings.DEFAULT_FROM_EMAIL}")
                print(f"To: {order.user.email}")
                print("Plain Message Preview:", plain_message[:200] + "...")
                
                # Send email
                email_result = send_mail(
                    subject=f'Order #{order.order_number} Cancelled',
                    message=plain_message,
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[order.user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                
                print(f"\nEmail send result: {email_result}")
                
                if email_result == 1:
                    print("Email sent successfully")
                    messages.success(request, "Order has been cancelled and customer has been notified.")
                else:
                    print("Email not sent (send_mail returned 0)")
                    messages.warning(request, "Order cancelled but email notification may not have been sent.")
                
            except Exception as email_error:
                print(f"\nError sending email:")
                print(f"Error type: {type(email_error).__name__}")
                print(f"Error message: {str(email_error)}")
                print(f"Error details: {repr(email_error)}")
                messages.warning(request, 
                    "Order has been cancelled but there was an error sending the notification email. "
                    "Please contact the customer directly."
                )
            
            return redirect('seller:order_detail', order_id=order.id)
            
        except Exception as e:
            print(f"\nError cancelling order:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print(f"Error details: {repr(e)}")
            messages.error(request, "There was an error cancelling the order. Please try again.")
            return redirect('seller:order_detail', order_id=order.id)
    
    return render(request, 'seller/cancel_order.html', {'order': order})

@login_required
def analytics(request):
    """Show seller analytics."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to access seller analytics.")
        return redirect('shop:home')
    
    # Get date range
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)  # Default to last 30 days
    
    # Handle custom date range
    date_range = request.GET.get('range')
    if date_range:
        if date_range == '7':
            start_date = end_date - timedelta(days=7)
        elif date_range == '90':
            start_date = end_date - timedelta(days=90)
        elif date_range == 'custom':
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            if start_date and end_date:
                start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get sales statistics
    sales_stats = OrderItem.objects.filter(
        product__seller=request.user,
        order__created_at__date__range=[start_date, end_date],
        order__status='DELIVERED'
    ).aggregate(
        total_amount=Sum('total'),
        total_quantity=Sum('quantity'),
        total_orders=Count('order', distinct=True),
        unique_buyers=Count('order__user', distinct=True)
    )
    
    # Calculate average order value
    if sales_stats['total_amount'] and sales_stats['total_orders']:
        sales_stats['avg_order_value'] = sales_stats['total_amount'] / sales_stats['total_orders']
    else:
        sales_stats['avg_order_value'] = 0
    
    # Get daily sales data for chart
    daily_sales = OrderItem.objects.filter(
        product__seller=request.user,
        order__created_at__date__range=[start_date, end_date],
        order__status='DELIVERED'
    ).values('order__created_at__date').annotate(
        amount=Sum('total'),
        orders=Count('order', distinct=True),
        quantity=Sum('quantity')
    ).order_by('order__created_at__date')
    
    # Prepare chart data
    dates = []
    amounts = []
    orders = []
    quantities = []
    for sale in daily_sales:
        dates.append(sale['order__created_at__date'].strftime('%Y-%m-%d'))
        amounts.append(float(sale['amount'] or 0))
        orders.append(sale['orders'])
        quantities.append(float(sale['quantity'] or 0))
    
    # Get top products
    top_products = Product.objects.filter(
        seller=request.user,
        order_items__order__status='DELIVERED',
        order_items__order__created_at__date__range=[start_date, end_date]
    ).annotate(
        total_sales=Sum('order_items__total'),
        total_quantity=Sum('order_items__quantity'),
        order_count=Count('order_items__order', distinct=True)
    ).order_by('-total_sales')[:10]
    
    # Get revenue by category
    revenue_by_category = Category.objects.filter(
        product__seller=request.user,
        product__order_items__order__status='DELIVERED',
        product__order_items__order__created_at__date__range=[start_date, end_date]
    ).annotate(
        total_sales=Sum('product__order_items__total'),
        total_quantity=Sum('product__order_items__quantity'),
        product_count=Count('product', distinct=True)
    ).order_by('-total_sales')
    
    context = {
        'title': 'Analytics',
        'start_date': start_date,
        'end_date': end_date,
        'sales_stats': sales_stats,
        'chart_data': {
            'dates': dates,
            'amounts': amounts,
            'orders': orders,
            'quantities': quantities
        },
        'top_products': top_products,
        'revenue_by_category': revenue_by_category,
    }
    return render(request, 'seller/analytics.html', context)

@login_required
def download_report(request, report_type):
    """Generate and download sales or products report."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to download reports.")
        return redirect('shop:home')
    
    # Get date range
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)  # Default to last 30 days
    
    # Handle custom date range
    date_range = request.GET.get('range')
    if date_range:
        if date_range == '7':
            start_date = end_date - timedelta(days=7)
        elif date_range == '90':
            start_date = end_date - timedelta(days=90)
        elif date_range == 'custom':
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            if start_date and end_date:
                start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
    
    import csv
    from django.http import HttpResponse
    
    if report_type == 'sales':
        # Generate sales report
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="sales_report_{start_date}_to_{end_date}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Order Number', 'Product', 'Quantity (kg)', 'Price per kg', 'Total'])
        
        order_items = OrderItem.objects.filter(
            product__seller=request.user,
            order__created_at__date__range=[start_date, end_date],
            order__status='DELIVERED'
        ).select_related('order', 'product').order_by('order__created_at')
        
        for item in order_items:
            writer.writerow([
                item.order.created_at.strftime('%Y-%m-%d'),
                item.order.order_number,
                item.product.name,
                item.quantity,
                item.price_per_kg,
                item.total
            ])
        
        return response
    
    elif report_type == 'products':
        # Generate products report
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="products_report_{start_date}_to_{end_date}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Product', 'Category', 'Total Sales', 'Total Quantity', 'Orders'])
        
        products = Product.objects.filter(
            seller=request.user,
            order_items__order__status='DELIVERED',
            order_items__order__created_at__date__range=[start_date, end_date]
        ).annotate(
            total_sales=Sum('order_items__total'),
            total_quantity=Sum('order_items__quantity'),
            order_count=Count('order_items__order', distinct=True)
        ).select_related('category')
        
        for product in products:
            writer.writerow([
                product.name,
                product.category.name,
                product.total_sales or 0,
                product.total_quantity or 0,
                product.order_count
            ])
        
        return response
    
    messages.error(request, "Invalid report type.")
    return redirect('seller:analytics')

@login_required
def profile(request):
    """Show seller profile."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('shop:home')
        
    # Test email functionality
    if request.GET.get('test_email') == '1':
        try:
            print("\n=== Testing Email Functionality ===")
            from django.core.mail import send_mail
            from django.conf import settings
            
            print(f"Sender: {settings.DEFAULT_FROM_EMAIL}")
            print(f"Recipient: {request.user.email}")
            print(f"Email Settings:")
            print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
            print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
            print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
            print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
            print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
            
            result = send_mail(
                subject='FISHLAND Test Email',
                message='This is a test email from FISHLAND to verify email functionality.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
                fail_silently=False,
            )
            
            print(f"\nEmail send result: {result}")
            if result == 1:
                messages.success(request, "Test email sent successfully! Please check your inbox.")
            else:
                messages.error(request, "Failed to send test email.")
                
        except Exception as e:
            print(f"Error sending test email:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            messages.error(request, f"Error sending test email: {str(e)}")
    
    context = {
        'title': 'My Profile',
        'user': request.user,
    }
    return render(request, 'seller/profile.html', context)

@login_required
def seller_settings(request):
    """Show seller settings."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to access seller settings.")
        return redirect('shop:home')
    return render(request, 'seller/settings.html')

@login_required
def update_notification_settings(request):
    """Update seller notification settings."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to update notification settings.")
        return redirect('shop:home')
    
    if request.method == 'POST':
        # Update notification settings
        request.user.seller_profile.email_order_updates = request.POST.get('email_order_updates', False) == 'on'
        request.user.seller_profile.email_product_updates = request.POST.get('email_product_updates', False) == 'on'
        request.user.seller_profile.email_marketing = request.POST.get('email_marketing', False) == 'on'
        request.user.seller_profile.save()
        
        messages.success(request, "Notification settings updated successfully.")
    
    return redirect('seller:settings')

@login_required
def update_payment_settings(request):
    """Update seller payment settings."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to update payment settings.")
        return redirect('shop:home')
    
    if request.method == 'POST':
        # Update payment settings
        request.user.seller_profile.bank_name = request.POST.get('bank_name', '')
        request.user.seller_profile.account_number = request.POST.get('account_number', '')
        request.user.seller_profile.ifsc_code = request.POST.get('ifsc_code', '')
        request.user.seller_profile.save()
        
        messages.success(request, "Payment settings updated successfully.")
    
    return redirect('seller:settings')

@login_required
def update_shipping_settings(request):
    """Update seller shipping settings."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to update shipping settings.")
        return redirect('shop:home')
    
    if request.method == 'POST':
        # Update shipping settings
        request.user.seller_profile.default_shipping_method = request.POST.get('default_shipping_method', '')
        request.user.seller_profile.free_shipping_threshold = request.POST.get('free_shipping_threshold', 0)
        request.user.seller_profile.save()
        
        messages.success(request, "Shipping settings updated successfully.")
    
    return redirect('seller:settings')

@login_required
def update_tax_settings(request):
    """Update seller tax settings."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to update tax settings.")
        return redirect('shop:home')
    
    if request.method == 'POST':
        # Update tax settings
        request.user.seller_profile.gst_number = request.POST.get('gst_number', '')
        request.user.seller_profile.pan_number = request.POST.get('pan_number', '')
        request.user.seller_profile.save()
        
        messages.success(request, "Tax settings updated successfully.")
    
    return redirect('seller:settings')

@login_required
def update_privacy_settings(request):
    """Update seller privacy settings."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to update privacy settings.")
        return redirect('shop:home')
    
    if request.method == 'POST':
        # Update privacy settings
        request.user.seller_profile.show_contact_info = request.POST.get('show_contact_info', False) == 'on'
        request.user.seller_profile.show_business_info = request.POST.get('show_business_info', False) == 'on'
        request.user.seller_profile.save()
        
        messages.success(request, "Privacy settings updated successfully.")
    
    return redirect('seller:settings')

@login_required
def add_product(request):
    """Add a new product."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to add products.")
        return redirect('shop:home')
    
    if request.method == 'POST':
        try:
            product = Product.objects.create(
                seller=request.user,
                name=request.POST.get('name'),
                description=request.POST.get('description'),
                category_id=request.POST.get('category'),
                price_per_kg=request.POST.get('price_per_kg'),
                minimum_order_quantity=request.POST.get('minimum_order_quantity'),
                stock_quantity=request.POST.get('stock_quantity'),
                image=request.FILES.get('image'),
                is_available=True,
                is_approved=False  # Seller-created products need admin approval
            )
            messages.success(request, f'Product "{product.name}" has been added and is pending approval.')
            return redirect('seller:products')
        except Exception as e:
            messages.error(request, f'Error adding product: {str(e)}')
    
    return redirect('seller:products')

@login_required
def edit_product(request, product_id):
    """Edit an existing product."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to edit products.")
        return redirect('shop:home')
    
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        try:
            product.name = request.POST.get('name')
            product.description = request.POST.get('description')
            product.category_id = request.POST.get('category')
            product.price_per_kg = request.POST.get('price_per_kg')
            product.minimum_order_quantity = request.POST.get('minimum_order_quantity')
            product.stock_quantity = request.POST.get('stock_quantity')
            
            if 'image' in request.FILES:
                product.image = request.FILES['image']
            
            product.is_available = bool(request.POST.get('is_available'))
            product.save()
            
            messages.success(request, f'Product "{product.name}" has been updated.')
            return redirect('seller:products')
        except Exception as e:
            messages.error(request, f'Error updating product: {str(e)}')
    
    return redirect('seller:products')

@login_required
def toggle_product(request, product_id):
    """Toggle product availability."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to manage products.")
        return redirect('shop:home')
    
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    product.is_available = not product.is_available
    product.save()
    
    status = "available" if product.is_available else "unavailable"
    messages.success(request, f'Product "{product.name}" is now {status}.')
    return redirect('seller:products')

@login_required
def stock_management(request):
    """Display and manage stock for all seller's products."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to access stock management.")
        return redirect('shop:home')

    # Get all products for the seller with related data
    products = Product.objects.filter(
        seller=request.user
    ).select_related('category').order_by('name')

    # Handle search
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    # Handle filtering
    filter_status = request.GET.get('status', '')
    if filter_status == 'low_stock':
        products = products.filter(stock_quantity__lte=F('stock_alert'))
    elif filter_status == 'out_of_stock':
        products = products.filter(stock_quantity=0)
    elif filter_status == 'in_stock':
        products = products.filter(stock_quantity__gt=0)

    # Pagination
    paginator = Paginator(products, 10)  # Show 10 products per page
    page = request.GET.get('page')
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    context = {
        'products': products,
        'search_query': search_query,
        'filter_status': filter_status,
    }
    return render(request, 'seller/stock_management.html', context)

@login_required
def update_stock(request, product_id):
    """Update stock quantity for a specific product."""
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        try:
            quantity = Decimal(request.POST.get('quantity', 0))
            change_type = request.POST.get('change_type', '').upper()
            reason = request.POST.get('reason', '')
            
            # Validate change_type
            valid_change_types = dict(StockHistory.STOCK_CHANGE_TYPES)
            if change_type not in valid_change_types:
                messages.error(request, "Invalid stock change type.")
                return redirect('seller:stock_management')
            
            # Calculate new quantity based on change type
            if change_type == 'ADDITION':
                new_quantity = product.stock_quantity + quantity
            elif change_type == 'REDUCTION':
                new_quantity = product.stock_quantity - quantity
                if new_quantity < 0:
                    messages.error(request, "Stock cannot be reduced below 0.")
                    return redirect('seller:stock_management')
            elif change_type == 'ADJUSTMENT':
                new_quantity = quantity
            else:
                messages.error(request, "Invalid stock change type.")
                return redirect('seller:stock_management')
            
            # Validate reason
            if not reason:
                messages.error(request, "Please provide a reason for the stock change.")
                return redirect('seller:stock_management')
            
            try:
                # Use the product's update_stock method which handles stock history and alerts
                print("\n=== Starting Stock Update ===")
                print(f"Product: {product.name}")
                print(f"Current Stock: {product.stock_quantity}kg")
                print(f"New Stock: {new_quantity}kg")
                print(f"Change Type: {change_type}")
                
                product.update_stock(new_quantity, change_type, reason, request.user)
                messages.success(request, f"Stock updated successfully for {product.name}")
                
                print("=== Stock Update Complete ===\n")
                
            except Exception as e:
                print(f"\nError in stock update:")
                print(f"Error type: {type(e).__name__}")
                print(f"Error message: {str(e)}")
                messages.error(request, f"Error updating stock: {str(e)}")
                return redirect('seller:stock_management')
            
        except (ValueError, TypeError) as e:
            messages.error(request, "Invalid quantity value provided.")
            return redirect('seller:stock_management')
            
    return redirect('seller:stock_management')

@login_required
def set_stock_alert(request, product_id):
    """Set stock alert threshold for a specific product."""
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        try:
            threshold = Decimal(request.POST.get('threshold_quantity', 0))
            is_active = request.POST.get('is_active') == 'on'
            
            if threshold < 0:
                messages.error(request, "Alert threshold cannot be negative.")
                return redirect('seller:stock_management')
            
            alert, created = StockAlert.objects.get_or_create(
                product=product,
                defaults={
                    'threshold_quantity': threshold,
                    'is_active': is_active,
                    'last_notification_sent': None
                }
            )
            
            if not created:
                alert.threshold_quantity = threshold
                alert.is_active = is_active
                # Reset last notification if alert is re-enabled or threshold changed
                if is_active and (not alert.is_active or alert.threshold_quantity != threshold):
                    alert.last_notification_sent = None
                alert.save()
            
            action = "enabled" if is_active else "disabled"
            messages.success(
                request,
                f"Stock alert {action} for {product.name}. You'll be notified when stock falls below {threshold}kg."
            )
            
            # Check if we should send an alert immediately
            if is_active and product.stock_quantity <= threshold:
                try:
                    product.notify_low_stock()
                    messages.info(
                        request,
                        f"Current stock ({product.stock_quantity}kg) is below the alert threshold. "
                        "A notification has been sent."
                    )
                except Exception as e:
                    messages.warning(
                        request,
                        f"Alert set but failed to send immediate notification: {str(e)}"
                    )
        
        except (ValueError, TypeError) as e:
            messages.error(request, "Invalid threshold value provided.")
        except Exception as e:
            messages.error(request, f"Error setting stock alert: {str(e)}")
    
    return redirect('seller:stock_management')

@login_required
def assign_delivery(request, order_id):
    """Assign a delivery agent to an order."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('shop:home')
    
    order = get_object_or_404(Order, id=order_id)
    
    # Verify the order belongs to products sold by this seller
    if not order.order_items.filter(product__seller=request.user).exists():
        messages.error(request, "You don't have permission to manage this order.")
        return redirect('seller:order_list')
    
    if request.method == 'POST':
        delivery_profile_id = request.POST.get('delivery_profile')
        if not delivery_profile_id:
            messages.error(request, 'Please select a delivery agent.')
            return redirect('seller:assign_delivery', order_id=order.id)
        
        try:
            delivery_profile = DeliveryProfile.objects.get(id=delivery_profile_id, status='ONLINE')
            
            # Update order and delivery agent status
            order.delivery_boy = delivery_profile
            order.status = 'ASSIGNED_TO_DELIVERY'
            order.delivery_assigned_at = timezone.now()
            order.save()
            
            delivery_profile.status = 'BUSY'
            delivery_profile.save()
            
            # Send notification email to delivery agent
            try:
                order.notify_delivery_assignment()
                messages.success(request, 
                    f'Order #{order.id} has been assigned to {delivery_profile.user.get_full_name()} '
                    'and notification email has been sent.'
                )
            except Exception as e:
                messages.warning(request, 
                    f'Order assigned but failed to send notification email: {str(e)}'
                )
            
            return redirect('seller:order_list')
            
        except DeliveryProfile.DoesNotExist:
            messages.error(request, 'Selected delivery agent is no longer available.')
            return redirect('seller:assign_delivery', order_id=order.id)
        except Exception as e:
            messages.error(request, f'Error assigning delivery agent: {str(e)}')
            return redirect('seller:assign_delivery', order_id=order.id)
    
    # Get list of available delivery agents with their performance metrics
    delivery_agents = DeliveryProfile.objects.filter(
        status='ONLINE',
        is_active=True,
        is_verified=True
    ).select_related('user').annotate(
        current_orders=Count(
            'assigned_orders',
            filter=Q(assigned_orders__status__in=['ASSIGNED_TO_DELIVERY', 'OUT_FOR_DELIVERY'])
        ),
        delivery_success_rate=Case(
            When(total_deliveries__gt=0,
                 then=ExpressionWrapper(
                     F('successful_deliveries') * 100.0 / F('total_deliveries'),
                     output_field=FloatField()
                 )
            ),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).order_by('-rating', '-delivery_success_rate')
    
    return render(request, 'seller/assign_delivery.html', {
        'order': order,
        'delivery_agents': delivery_agents
    })

@login_required
def order_detail(request, order_id):
    """Show order details."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('shop:home')
    
    order = get_object_or_404(Order, id=order_id)
    
    # Verify the order belongs to products sold by this seller
    if not order.order_items.filter(product__seller=request.user).exists():
        messages.error(request, "You don't have permission to view this order.")
        return redirect('seller:order_list')
    
    # Get order items for this seller
    order_items = order.order_items.filter(product__seller=request.user)
    
    context = {
        'order': order,
        'order_items': order_items
    }
    return render(request, 'seller/order_detail.html', context)

@login_required
def change_password(request):
    """Change seller's password."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('shop:home')
        
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        if not current_password or not new_password1 or not new_password2:
            messages.error(request, "Please fill in all password fields.")
            return redirect('seller:profile')
            
        if new_password1 != new_password2:
            messages.error(request, "New passwords don't match.")
            return redirect('seller:profile')
            
        if len(new_password1) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('seller:profile')
            
        # Check if current password is correct
        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect('seller:profile')
            
        # Change password
        request.user.set_password(new_password1)
        request.user.save()
        
        # Update session to prevent logout
        update_session_auth_hash(request, request.user)
        
        messages.success(request, "Password changed successfully.")
        return redirect('seller:profile')
        
    return redirect('seller:profile')

@login_required
def upload_profile_picture(request):
    """Handle profile picture upload for seller."""
    if not request.user.is_seller:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('shop:home')
        
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        profile_picture = request.FILES['profile_picture']
        
        # Validate file size (5MB limit)
        if profile_picture.size > 5 * 1024 * 1024:  # 5MB in bytes
            messages.error(request, "File size too large. Maximum size is 5MB.")
            return redirect('seller:profile')
            
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif']
        if profile_picture.content_type not in allowed_types:
            messages.error(request, "Invalid file type. Please upload a JPEG, PNG or GIF image.")
            return redirect('seller:profile')
            
        try:
            # Delete old profile picture if it exists
            if request.user.profile_picture:
                request.user.profile_picture.delete(save=False)
                
            # Save new profile picture
            request.user.profile_picture = profile_picture
            request.user.save()
            
            messages.success(request, "Profile picture updated successfully.")
            
        except Exception as e:
            messages.error(request, "An error occurred while uploading the profile picture. Please try again.")
            
    return redirect('seller:profile')
