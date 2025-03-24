from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import Order, OrderItem, Address
from cart.models import Cart, CartItem
from products.models import Product
from decimal import Decimal
import razorpay
from django.conf import settings
from django.http import JsonResponse
import json
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.template.loader import render_to_string

def send_order_confirmation_email(order):
    """Send order confirmation email to customer"""
    subject = f'Order Confirmation - Order #{order.order_number}'
    
    # Prepare email context
    context = {
        'order': order,
        'order_items': order.order_items.all(),
        'delivery_address': order.delivery_address,
    }
    
    # Render email content from template
    html_message = render_to_string('orders/email/order_confirmation.html', context)
    plain_message = render_to_string('orders/email/order_confirmation.txt', context)
    
    try:
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=False,
        )
        print(f"Order confirmation email sent to {order.user.email}")
    except Exception as e:
        print(f"Failed to send order confirmation email: {str(e)}")
        # Don't raise the exception - we don't want to block order placement if email fails

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@login_required
def checkout(request):
    # Get user's cart
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related('product').all()
    
    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart:view')
    
    # Get user's addresses
    addresses = Address.objects.filter(user=request.user).order_by('-is_default')
    
    # Calculate totals
    subtotal = sum(item.total for item in cart_items)
    delivery_fee = Decimal('0.00') if subtotal >= Decimal('1000.00') else Decimal('50.00')
    total = subtotal + delivery_fee
    
    # Create Razorpay order
    try:
        razorpay_order = razorpay_client.order.create({
            'amount': int(float(total) * 100),  # Convert to paise
            'currency': 'INR',
            'payment_capture': '1'
        })
        razorpay_order_id = razorpay_order['id']
    except Exception as e:
        messages.error(request, 'Unable to initialize payment. Please try again.')
        return redirect('cart:view')
    
    # Check for stock issues
    has_stock_issues = any(item.quantity > item.product.stock_quantity for item in cart_items)
    if has_stock_issues:
        messages.warning(request, 'Some items in your cart have stock availability issues.')
    
    # Get available delivery slots (next 7 days, 8 AM to 8 PM)
    current_time = timezone.localtime()
    
    # Generate available dates (next 7 days)
    available_dates = []
    start_date = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    if current_time.hour >= 14:  # After 2 PM, start from next day
        start_date += timedelta(days=1)
    
    for day in range(7):
        date = start_date + timedelta(days=day)
        available_dates.append({
            'date': date.strftime('%Y-%m-%d'),
            'day': date.strftime('%a'),
            'date_num': date.strftime('%d'),
            'month': date.strftime('%b'),
            'full_date': date.strftime('%B %d, %Y'),
            'is_today': date.date() == current_time.date()
        })
    
    # Generate available time slots (8 AM to 8 PM, 2-hour slots)
    available_times = [
        '08:00-10:00',
        '10:00-12:00',
        '12:00-14:00',
        '14:00-16:00',
        '16:00-18:00',
        '18:00-20:00'
    ]
    
    context = {
        'addresses': addresses,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'total': total,
        'has_stock_issues': has_stock_issues,
        'available_dates': available_dates,
        'available_times': available_times,
        'razorpay_order_id': razorpay_order_id,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'callback_url': request.build_absolute_uri('/orders/payment/verify/')
    }
    
    return render(request, 'orders/checkout.html', context)

@login_required
@transaction.atomic
def place_order(request):
    if request.method != 'POST':
        return redirect('orders:checkout')
    
    print("\n=== Starting Order Placement ===")
    print("POST data:", request.POST)
    
    # Get payment method and form data
    payment_method = request.POST.get('payment_method')
    address_id = request.POST.get('address_id')
    delivery_date = request.POST.get('delivery_date')
    delivery_time = request.POST.get('delivery_time')
    
    print("\nForm Data:")
    print(f"Payment Method: {payment_method}")
    print(f"Address ID: {address_id}")
    print(f"Delivery Date: {delivery_date}")
    print(f"Delivery Time: {delivery_time}")
    
    # Validate form data
    if not all([payment_method, address_id, delivery_date, delivery_time]):
        print("Missing form data")
        messages.error(request, 'Please fill in all required fields.')
        return redirect('orders:checkout')
    
    # For online payment, verify Razorpay payment
    razorpay_payment_id = None
    razorpay_order_id = None
    razorpay_signature = None
    
    if payment_method == 'online':
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_signature = request.POST.get('razorpay_signature')
        
        print("\nRazorpay Data:")
        print(f"Payment ID: {razorpay_payment_id}")
        print(f"Order ID: {razorpay_order_id}")
        print(f"Signature: {razorpay_signature}")
        
        if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
            print("Missing Razorpay data")
            messages.error(request, 'Payment verification failed. Please try again.')
            return redirect('orders:checkout')
        
        try:
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
            print("Razorpay payment verification successful")
        except Exception as e:
            print(f"Razorpay payment verification failed: {str(e)}")
            messages.error(request, 'Payment verification failed. Please try again.')
            return redirect('orders:checkout')
    
    try:
        # Get user's cart with all related data
        cart = Cart.objects.select_related('user').prefetch_related(
            'items__product__seller'
        ).get(user=request.user)
        
        cart_items = cart.items.all()
        if not cart_items.exists():
            messages.error(request, 'Your cart is empty.')
            return redirect('cart:view')
        
        print("\nCart Items:")
        for item in cart_items:
            print(f"- {item.product.name}: {item.quantity}kg at ₹{item.product.price_per_kg}/kg (Seller: {item.product.seller.get_full_name()})")
        
        # Check stock availability
        stock_issues = []
        for item in cart_items:
            if item.quantity > item.product.stock_quantity:
                stock_issues.append(
                    f"{item.product.name}: Only {item.product.stock_quantity}kg available"
                )
        
        if stock_issues:
            print("\nStock Issues:", stock_issues)
            messages.error(request, "Stock availability issues:\n" + "\n".join(stock_issues))
            return redirect('cart:view')
        
        # Get delivery address
        try:
            address = Address.objects.get(id=address_id, user=request.user)
            print("\nDelivery Address:", address)
        except Address.DoesNotExist:
            print(f"Invalid address ID: {address_id}")
            messages.error(request, 'Invalid delivery address.')
            return redirect('orders:checkout')
        
        # Calculate totals
        subtotal = sum(item.total for item in cart_items)
        delivery_fee = Decimal('0.00') if subtotal >= Decimal('1000.00') else Decimal('50.00')
        total = subtotal + delivery_fee
        
        print("\nOrder Totals:")
        print(f"Subtotal: ₹{subtotal}")
        print(f"Delivery Fee: ₹{delivery_fee}")
        print(f"Total: ₹{total}")
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            delivery_address=address,
            delivery_date=delivery_date,
            delivery_time=delivery_time,
            payment_method='RAZORPAY' if payment_method == 'online' else 'COD',
            payment_status='PAID' if payment_method == 'online' else 'PENDING',
            status='CONFIRMED',
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=total,
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
            confirmed_at=timezone.now()
        )
        print("\nOrder created:", order)
        
        # Create order items and update stock in a single transaction
        order_items = []
        for cart_item in cart_items:
            # Create order item
            order_item = OrderItem(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price_per_kg=cart_item.product.price_per_kg,
                total=cart_item.total
            )
            order_items.append(order_item)
            
            # Update product stock
            product = cart_item.product
            product.stock_quantity = models.F('stock_quantity') - cart_item.quantity
            product.save(update_fields=['stock_quantity'])
            
            print(f"Updated stock for {product.name}: reduced by {cart_item.quantity}kg")
        
        # Bulk create order items
        OrderItem.objects.bulk_create(order_items)
        print("Order items created")
        
        # Refresh products to get updated stock quantities
        for item in cart_items:
            item.product.refresh_from_db()
            print(f"Current stock for {item.product.name}: {item.product.stock_quantity}kg")
        
        # Clear cart
        cart.items.all().delete()
        print("Cart cleared")
        
        # Send confirmation email
        try:
            send_order_confirmation_email(order)
            print("Order confirmation email sent")
        except Exception as e:
            print(f"Error sending confirmation email: {str(e)}")
        
        print("\nOrder placement successful!")
        print(f"Redirecting to confirmation page for Order #{order.id}")
        
        messages.success(request, 'Order placed successfully!')
        return redirect('orders:order_confirmation', order_id=order.id)
        
    except Exception as e:
        print(f"\nError placing order: {str(e)}")
        import traceback
        print("Traceback:", traceback.format_exc())
        messages.error(request, 'An error occurred while placing your order. Please try again.')
        return redirect('orders:checkout')

@login_required
def order_confirmation(request, order_id):
    try:
        # Get the order with all related data
        order = Order.objects.select_related(
            'user',
            'delivery_address'
        ).prefetch_related(
            'order_items__product__seller'
        ).get(id=order_id, user=request.user)
        
        # Get order items
        order_items = order.order_items.all()
        
        context = {
            'order': order,
            'order_items': order_items,
            'subtotal': order.subtotal,
            'delivery_fee': order.delivery_fee,
            'total': order.total
        }
        
        return render(request, 'orders/order_confirmation.html', context)
    except Order.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('orders:order_history')

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    context = {
        'order': order,
        'order_items': order.order_items.all().select_related('product'),
    }
    
    return render(request, 'orders/order_detail.html', context)

@login_required
def order_history(request):
    """View for displaying user's order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/order_history.html', {'orders': orders})

@login_required
def manage_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Check if any items belong to this seller
    if not order.order_items.filter(product__seller=request.user).exists():
        messages.error(request, "You don't have permission to manage this order.")
        return redirect('seller:order_list')
    
    context = {
        'order': order,
        'order_items': order.order_items.all().select_related('product'),
    }
    
    return render(request, 'orders/manage_order.html', context)
