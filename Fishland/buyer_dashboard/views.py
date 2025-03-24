from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, F, Count
from django.utils import timezone
from products.models import Product, Category
from orders.models import Order, OrderItem
from cart.models import Cart, CartItem
from .models import SavedProduct, ProductNotification
from accounts.models import Address
from decimal import Decimal

@login_required
def dashboard(request):
    # Get user's total orders
    total_orders = Order.objects.filter(user=request.user).count()
    
    # Get user's recent orders
    recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Get saved products with stock status
    saved_products = SavedProduct.objects.filter(user=request.user).select_related('product')
    
    # Get active notifications
    active_notifications = ProductNotification.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('product')
    
    # Get addresses count
    addresses_count = Address.objects.filter(user=request.user).count()
    
    context = {
        'total_orders': total_orders,
        'recent_orders': recent_orders,
        'saved_products': saved_products,
        'notifications': active_notifications,
        'addresses_count': addresses_count,
    }
    return render(request, 'buyer_dashboard/dashboard.html', context)

@login_required
def product_list(request):
    products = Product.objects.filter(is_approved=True, is_available=True)
    
    # Apply filters
    category = request.GET.get('category')
    if category:
        products = products.filter(category_id=category)
    
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price_per_kg__gte=min_price)
    if max_price:
        products = products.filter(price_per_kg__lte=max_price)
    
    # Stock filter
    stock_status = request.GET.get('stock')
    if stock_status == 'in_stock':
        products = products.filter(stock_quantity__gt=0)
    elif stock_status == 'out_of_stock':
        products = products.filter(stock_quantity=0)
    
    # Search
    search_query = request.GET.get('q')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(seller__business_name__icontains=search_query)
        )
    
    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    products = products.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(products, 12)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    context = {
        'products': products,
        'categories': Category.objects.all(),
        'current_category': category,
        'current_stock_status': stock_status,
        'search_query': search_query
    }
    return render(request, 'buyer_dashboard/product_list.html', context)

@login_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_approved=True)
    is_saved = SavedProduct.objects.filter(user=request.user, product=product).exists()
    has_notification = ProductNotification.objects.filter(
        user=request.user,
        product=product,
        is_active=True
    ).exists()
    
    context = {
        'product': product,
        'is_saved': is_saved,
        'has_notification': has_notification,
        'related_products': Product.objects.filter(
            category=product.category,
            is_approved=True,
            is_available=True
        ).exclude(id=product.id)[:4]
    }
    return render(request, 'buyer_dashboard/product_detail.html', context)

@login_required
def quick_order(request, product_id):
    if request.method != 'POST':
        return redirect('buyer_dashboard:product_detail', product_id=product_id)
    
    product = get_object_or_404(Product, id=product_id, is_approved=True, is_available=True)
    quantity = Decimal(request.POST.get('quantity', 0))
    
    # Validate quantity
    if quantity < product.minimum_order_quantity:
        messages.error(request, f"Minimum order quantity is {product.minimum_order_quantity}kg")
        return redirect('buyer_dashboard:product_detail', product_id=product_id)
    
    if quantity > product.stock_quantity:
        messages.error(request, f"Only {product.stock_quantity}kg available in stock")
        return redirect('buyer_dashboard:product_detail', product_id=product_id)
    
    # Add to cart
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )
    
    if not created:
        cart_item.quantity = quantity
        cart_item.save()
    
    messages.success(request, f"Added {quantity}kg of {product.name} to cart")
    return redirect('cart:view')

@login_required
def save_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_approved=True)
    SavedProduct.objects.get_or_create(user=request.user, product=product)
    messages.success(request, f"{product.name} added to saved products")
    return redirect('buyer_dashboard:product_detail', product_id=product_id)

@login_required
def unsave_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    SavedProduct.objects.filter(user=request.user, product=product).delete()
    messages.success(request, f"{product.name} removed from saved products")
    return redirect('buyer_dashboard:product_detail', product_id=product_id)

@login_required
def set_notification(request, product_id):
    if request.method != 'POST':
        return redirect('buyer_dashboard:product_detail', product_id=product_id)
    
    product = get_object_or_404(Product, id=product_id, is_approved=True)
    notification_type = request.POST.get('notification_type')
    target_price = request.POST.get('target_price')
    
    if notification_type not in [t[0] for t in ProductNotification.NOTIFICATION_TYPES]:
        messages.error(request, "Invalid notification type")
        return redirect('buyer_dashboard:product_detail', product_id=product_id)
    
    notification, created = ProductNotification.objects.get_or_create(
        user=request.user,
        product=product,
        notification_type=notification_type,
        defaults={
            'target_price': target_price if notification_type == 'PRICE' else None
        }
    )
    
    if not created:
        notification.is_active = True
        if notification_type == 'PRICE':
            notification.target_price = target_price
        notification.save()
    
    messages.success(request, f"You will be notified when {product.name} is {notification.get_notification_type_display().lower()}")
    return redirect('buyer_dashboard:product_detail', product_id=product_id)

@login_required
def delete_notification(request, notification_id):
    notification = get_object_or_404(ProductNotification, id=notification_id, user=request.user)
    notification.delete()
    messages.success(request, "Notification removed successfully")
    return redirect('buyer_dashboard:notifications')

@login_required
def notifications(request):
    notifications = ProductNotification.objects.filter(
        user=request.user
    ).select_related('product').order_by('-created_at')
    
    return render(request, 'buyer_dashboard/notifications.html', {
        'notifications': notifications
    })
