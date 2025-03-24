from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count
from .models import Product, StockHistory, StockAlert
from django.utils import timezone
from decimal import Decimal

def is_seller(user):
    return user.is_authenticated and user.role == 'SELLER'

@login_required
@user_passes_test(is_seller, login_url='accounts:login')
def seller_dashboard(request):
    """Display seller's dashboard with product and stock information."""
    products = Product.objects.filter(seller=request.user)
    
    # Get stock statistics
    total_products = products.count()
    low_stock_products = products.filter(stock_quantity__lte=10).count()
    out_of_stock_products = products.filter(stock_quantity=0).count()
    
    # Get recent stock updates
    recent_stock_updates = StockHistory.objects.filter(
        product__seller=request.user
    ).order_by('-created_at')[:5]
    
    context = {
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'recent_stock_updates': recent_stock_updates
    }
    return render(request, 'products/seller/dashboard.html', context)

@login_required
@user_passes_test(is_seller, login_url='accounts:login')
def stock_management(request):
    """Display and manage stock for all seller's products."""
    products = Product.objects.filter(seller=request.user).order_by('-created_at')
    
    # Handle search
    query = request.GET.get('q')
    if query:
        products = products.filter(name__icontains=query)
    
    # Handle filters
    stock_filter = request.GET.get('stock_status')
    if stock_filter == 'low':
        products = products.filter(stock_quantity__lte=10)
    elif stock_filter == 'out':
        products = products.filter(stock_quantity=0)
    
    # Pagination
    paginator = Paginator(products, 10)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    context = {
        'products': products,
        'stock_filter': stock_filter,
        'search_query': query
    }
    return render(request, 'products/seller/stock_management.html', context)

@login_required
@user_passes_test(is_seller, login_url='accounts:login')
def update_stock(request, product_id):
    """Update stock quantity for a specific product."""
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        quantity = Decimal(request.POST.get('quantity', 0))
        change_type = request.POST.get('change_type')
        reason = request.POST.get('reason')
        
        if change_type == 'ADDITION':
            new_quantity = product.stock_quantity + quantity
        elif change_type == 'REDUCTION':
            new_quantity = product.stock_quantity - quantity
            if new_quantity < 0:
                messages.error(request, "Stock cannot be reduced below 0.")
                return redirect('products:stock_management')
        else:  # ADJUSTMENT
            new_quantity = quantity
        
        product.update_stock(new_quantity, change_type, reason, request.user)
        messages.success(request, f"Stock updated successfully for {product.name}")
        
        return redirect('products:stock_management')
    
    # Get stock history for this product
    stock_history = StockHistory.objects.filter(product=product).order_by('-created_at')[:10]
    
    context = {
        'product': product,
        'stock_history': stock_history
    }
    return render(request, 'products/seller/update_stock.html', context)

@login_required
@user_passes_test(is_seller, login_url='accounts:login')
def manage_stock_alerts(request, product_id):
    """Manage stock alerts for a specific product."""
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        threshold = Decimal(request.POST.get('threshold_quantity', 0))
        is_active = request.POST.get('is_active') == 'on'
        
        alert, created = StockAlert.objects.get_or_create(
            product=product,
            defaults={'threshold_quantity': threshold, 'is_active': is_active}
        )
        
        if not created:
            alert.threshold_quantity = threshold
            alert.is_active = is_active
            alert.save()
        
        messages.success(request, f"Stock alert settings updated for {product.name}")
        return redirect('products:stock_management')
    
    # Get or initialize stock alert
    try:
        stock_alert = product.stock_alert
    except StockAlert.DoesNotExist:
        stock_alert = None
    
    context = {
        'product': product,
        'stock_alert': stock_alert
    }
    return render(request, 'products/seller/manage_stock_alerts.html', context)
