from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
from accounts.models import User
from products.models import Product, Category, StockAlert, StockHistory
from orders.models import Order, OrderItem
import json
from decimal import Decimal

def is_seller(user):
    return user.is_authenticated and user.role == 'SELLER'

@login_required
@user_passes_test(is_seller)
def dashboard(request):
    today = timezone.now()
    thirty_days_ago = today - timedelta(days=30)
    
    # Get seller's products
    seller_products = Product.objects.filter(seller=request.user)
    
    # Get orders containing seller's products
    seller_orders = Order.objects.filter(
        order_items__product__in=seller_products
    ).distinct()
    
    # Calculate statistics
    context = {
        'total_products': seller_products.count(),
        'active_products': seller_products.filter(is_approved=True, is_available=True).count(),
        'pending_products': seller_products.filter(is_approved=False).count(),
        'total_orders': seller_orders.count(),
        'orders_today': seller_orders.filter(created_at__date=today.date()).count(),
        'total_revenue': OrderItem.objects.filter(
            product__in=seller_products,
            order__status='DELIVERED'
        ).aggregate(total_sum=Sum('total'))['total_sum'] or 0,
        'revenue_today': OrderItem.objects.filter(
            product__in=seller_products,
            order__status='DELIVERED',
            order__created_at__date=today.date()
        ).aggregate(total_sum=Sum('total'))['total_sum'] or 0,
    }
    
    # Get low stock items
    low_stock_items = Product.objects.filter(
        seller=request.user,
        stock_alert__is_active=True,
        stock_quantity__lte=F('stock_alert__threshold_quantity')
    ).select_related('stock_alert').order_by('stock_quantity')
    
    context['low_stock_items'] = low_stock_items
    
    # Recent Orders
    context['recent_orders'] = seller_orders.select_related('user').order_by('-created_at')[:5]
    
    # Sales Chart Data
    sales_data = []
    sales_labels = []
    for i in range(30):
        date = today - timedelta(days=i)
        amount = OrderItem.objects.filter(
            product__in=seller_products,
            order__status='DELIVERED',
            order__created_at__date=date.date()
        ).aggregate(total_sum=Sum('total'))['total_sum'] or 0
        sales_data.insert(0, float(amount))
        sales_labels.insert(0, date.strftime('%b %d'))
    
    context['sales_data'] = sales_data
    context['sales_labels'] = json.dumps(sales_labels)
    
    # Top Products
    context['top_products'] = Product.objects.filter(
        id__in=seller_products,
        order_items__order__status='DELIVERED'
    ).annotate(
        total_sales=Sum('order_items__total'),
        total_quantity=Sum('order_items__quantity')
    ).order_by('-total_sales')[:5]
    
    return render(request, 'seller/dashboard.html', context)

@login_required
@user_passes_test(is_seller)
def products(request):
    products_list = Product.objects.filter(seller=request.user)
    
    # Apply filters
    category = request.GET.get('category')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if category:
        products_list = products_list.filter(category_id=category)
    
    if status:
        if status == 'active':
            products_list = products_list.filter(is_approved=True, is_available=True)
        elif status == 'pending':
            products_list = products_list.filter(is_approved=False)
        elif status == 'unavailable':
            products_list = products_list.filter(is_available=False)
    
    if search:
        products_list = products_list.filter(
            Q(name__icontains=search) |
            Q(category__name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(products_list.order_by('-created_at'), 10)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    # Get categories for filter
    categories = Category.objects.all()
    
    return render(request, 'seller/products.html', {
        'products': products,
        'categories': categories
    })

@login_required
@user_passes_test(is_seller)
def orders(request):
    # Get seller's products
    seller_products = Product.objects.filter(seller=request.user)
    
    # Get orders containing seller's products
    orders_list = Order.objects.filter(
        order_items__product__in=seller_products
    ).distinct()
    
    # Apply filters
    status = request.GET.get('status')
    search = request.GET.get('search')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if status:
        orders_list = orders_list.filter(status=status)
    
    if search:
        orders_list = orders_list.filter(
            Q(id__icontains=search) |
            Q(buyer__email__icontains=search)
        )
    
    if date_from:
        orders_list = orders_list.filter(created_at__date__gte=date_from)
    
    if date_to:
        orders_list = orders_list.filter(created_at__date__lte=date_to)
    
    # Pagination
    paginator = Paginator(orders_list.order_by('-created_at'), 10)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    return render(request, 'seller/orders.html', {'orders': orders})

@login_required
@user_passes_test(is_seller)
def analytics(request):
    # Get date range
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    if request.GET.get('start_date'):
        start_date = timezone.datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d')
    if request.GET.get('end_date'):
        end_date = timezone.datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d')
    
    # Get seller's products
    seller_products = Product.objects.filter(seller=request.user)
    
    # Sales Statistics
    sales_stats = OrderItem.objects.filter(
        product__in=seller_products,
        order__status='DELIVERED',
        order__created_at__date__range=[start_date, end_date]
    ).aggregate(
        total_amount=Sum('total'),
        total_quantity=Sum('quantity'),
        total_orders=Count('order', distinct=True)
    )
    
    # Top Products
    top_products = Product.objects.filter(
        id__in=seller_products,
        order_items__order__status='DELIVERED',
        order_items__order__created_at__date__range=[start_date, end_date]
    ).annotate(
        total_quantity=Sum('order_items__quantity'),
        total_sales=Sum('order_items__total')
    ).order_by('-total_sales')[:10]
    
    # Top Buyers
    top_buyers = User.objects.filter(
        role='BUYER',
        buyer_orders__status='DELIVERED',
        buyer_orders__order_items__product__in=seller_products,
        buyer_orders__created_at__date__range=[start_date, end_date]
    ).annotate(
        total_spent=Sum('buyer_orders__order_items__total'),
        order_count=Count('buyer_orders', distinct=True)
    ).order_by('-total_spent')[:10]
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'sales_stats': sales_stats,
        'top_products': top_products,
        'top_buyers': top_buyers
    }
    
    return render(request, 'seller/analytics.html', context)

@login_required
def stock_analytics(request):
    # Get all products for the seller
    products = Product.objects.filter(seller=request.user)
    
    # Calculate statistics
    total_products = products.count()
    in_stock_products = products.filter(stock_quantity__gt=0).count()
    out_of_stock_products = products.filter(stock_quantity=0).count()
    
    # Get products with stock alerts
    low_stock_alerts = StockAlert.objects.filter(
        product__seller=request.user,
        is_active=True,
        product__stock_quantity__lte=F('threshold_quantity')
    ).select_related('product')
    
    low_stock_products = low_stock_alerts.count()
    
    # Get recent stock history
    recent_stock_history = StockHistory.objects.filter(
        product__seller=request.user
    ).select_related('product', 'changed_by').order_by('-created_at')[:10]
    
    # Prepare data for stock levels chart
    product_data = products.values_list('name', 'stock_quantity')
    product_names = [product[0] for product in product_data]
    stock_levels = [float(product[1]) for product in product_data]
    
    context = {
        'total_products': total_products,
        'in_stock_products': in_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'low_stock_products': low_stock_products,
        'low_stock_alerts': low_stock_alerts,
        'recent_stock_history': recent_stock_history,
        'product_names': json.dumps(product_names),
        'stock_levels': json.dumps(stock_levels),
    }
    
    return render(request, 'seller_dashboard/stock_analytics.html', context)

@login_required
def sales_analytics(request):
    # Implementation for sales analytics
    return render(request, 'seller_dashboard/sales_analytics.html')

@login_required
def manage_stock(request, product_id):
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        quantity = Decimal(request.POST.get('quantity', 0))
        reason = request.POST.get('reason', '')
        
        if action == 'add':
            new_quantity = product.stock_quantity + quantity
            change_type = 'ADDITION'
        elif action == 'reduce':
            new_quantity = product.stock_quantity - quantity
            change_type = 'REDUCTION'
        else:
            new_quantity = quantity
            change_type = 'ADJUSTMENT'
            
        if new_quantity < 0:
            messages.error(request, 'Stock quantity cannot be negative.')
            return redirect('seller_dashboard:manage_stock', product_id=product_id)
            
        product.update_stock(new_quantity, change_type, reason, request.user)
        messages.success(request, 'Stock updated successfully.')
        return redirect('seller_dashboard:manage_stock', product_id=product_id)
    
    stock_history = product.stock_history.all()[:10]  # Get last 10 stock changes
    context = {
        'product': product,
        'stock_history': stock_history,
    }
    return render(request, 'seller_dashboard/manage_stock.html', context)

@login_required
def manage_stock_alert(request, product_id):
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        threshold = Decimal(request.POST.get('threshold', 0))
        is_active = bool(request.POST.get('is_active', False))
        
        alert, created = StockAlert.objects.get_or_create(
            product=product,
            defaults={'threshold_quantity': threshold, 'is_active': is_active}
        )
        
        if not created:
            alert.threshold_quantity = threshold
            alert.is_active = is_active
            alert.save()
            
        messages.success(request, 'Stock alert settings updated successfully.')
        return redirect('seller_dashboard:manage_stock', product_id=product_id)
        
    context = {
        'product': product,
        'alert': getattr(product, 'stock_alert', None)
    }
    return render(request, 'seller_dashboard/manage_stock_alert.html', context)
