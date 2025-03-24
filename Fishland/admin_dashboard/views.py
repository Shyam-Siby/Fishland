from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.db.models import Sum, Count, Q, F
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db import transaction
import json
import logging
import traceback

from accounts.models import User
from products.models import Product, Category
from orders.models import Order, OrderItem

logger = logging.getLogger(__name__)

def is_admin(user):
    return user.is_authenticated and user.role == 'ADMIN'

@login_required
@user_passes_test(is_admin)
def dashboard(request):
    # Get current date and 30 days ago
    today = timezone.now()
    thirty_days_ago = today - timezone.timedelta(days=30)
    
    # Get recent orders
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:5]
    
    # Get pending products
    pending_products = Product.objects.select_related('seller').filter(is_approved=False).order_by('-created_at')[:5]
    
    # Get categories and sellers for Add Product modal
    categories = Category.objects.all()
    sellers = User.objects.filter(role='SELLER')
    
    # Statistics
    context = {
        'total_users': User.objects.count(),
        'new_users_today': User.objects.filter(date_joined__date=today.date()).count(),
        'total_orders': Order.objects.count(),
        'orders_today': Order.objects.filter(created_at__date=today.date()).count(),
        'total_products': Product.objects.count(),
        'pending_approvals': Product.objects.filter(is_approved=False).count(),
        'total_revenue': Order.objects.filter(status='DELIVERED').aggregate(Sum('total'))['total__sum'] or 0,
        'revenue_today': Order.objects.filter(status='DELIVERED', created_at__date=today.date()).aggregate(Sum('total'))['total__sum'] or 0,
        'recent_orders': recent_orders,
        'pending_products': pending_products,
        'categories': categories,
        'sellers': sellers,
    }
    
    # Sales Chart Data (last 30 days)
    sales_data = []
    sales_labels = []
    for i in range(30):
        date = today - timezone.timedelta(days=i)
        amount = Order.objects.filter(
            created_at__date=date.date(),
            status='DELIVERED'
        ).aggregate(Sum('total'))['total__sum'] or 0
        sales_data.insert(0, float(amount))
        sales_labels.insert(0, date.strftime('%b %d'))
    
    context['sales_data'] = sales_data
    context['sales_labels'] = json.dumps(sales_labels)
    
    # Category Distribution
    categories = Category.objects.annotate(
        product_count=Count('product')
    ).order_by('-product_count')[:5]
    
    context['category_labels'] = json.dumps([cat.name for cat in categories])
    context['category_data'] = [cat.product_count for cat in categories]
    
    return render(request, 'admin/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def users(request):
    users_list = User.objects.all()
    
    # Apply filters
    role = request.GET.get('role')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if role:
        users_list = users_list.filter(role=role)
    
    if status:
        if status == 'active':
            users_list = users_list.filter(is_active=True)
        elif status == 'inactive':
            users_list = users_list.filter(is_active=False)
    
    if search:
        users_list = users_list.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(users_list.order_by('-date_joined'), 10)
    page = request.GET.get('page')
    users = paginator.get_page(page)
    
    return render(request, 'admin/users.html', {'users': users})

@login_required
@user_passes_test(is_admin)
def products(request):
    if request.method == 'POST':
        # Handle product creation
        try:
            product = Product.objects.create(
                name=request.POST.get('name'),
                description=request.POST.get('description'),
                category_id=request.POST.get('category'),
                seller_id=request.POST.get('seller'),
                price_per_kg=request.POST.get('price_per_kg'),
                minimum_order_quantity=request.POST.get('minimum_order_quantity'),
                stock_quantity=request.POST.get('stock_quantity'),
                image=request.FILES.get('image'),
                is_available=bool(request.POST.get('is_available')),
                is_approved=True  # Admin-created products are auto-approved
            )
            messages.success(request, f'Product "{product.name}" created successfully!')
            return redirect('admin_dashboard:products')
        except Exception as e:
            messages.error(request, f'Error creating product: {str(e)}')
            return redirect('admin_dashboard:dashboard')

    products_list = Product.objects.select_related('seller', 'category')
    
    # Apply filters
    category = request.GET.get('category')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if category:
        products_list = products_list.filter(category_id=category)
    
    if status:
        if status == 'approved':
            products_list = products_list.filter(is_approved=True, is_available=True)
        elif status == 'pending':
            products_list = products_list.filter(is_approved=False)
        elif status == 'unavailable':
            products_list = products_list.filter(is_available=False)
    
    if search:
        products_list = products_list.filter(
            Q(name__icontains=search) |
            Q(seller__email__icontains=search) |
            Q(category__name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(products_list.order_by('-created_at'), 10)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    # Get all categories for filter dropdown
    categories = Category.objects.all()
    
    # Get all sellers for product creation
    sellers = User.objects.filter(role='SELLER', is_active=True)
    
    return render(request, 'admin/products.html', {
        'products': products,
        'categories': categories,
        'sellers': sellers
    })

@login_required
@user_passes_test(is_admin)
def orders(request):
    orders_list = Order.objects.select_related('user').prefetch_related('order_items')
    
    # Apply filters
    status = request.GET.get('status')
    search = request.GET.get('search')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if status:
        orders_list = orders_list.filter(status=status)
    
    if search:
        orders_list = orders_list.filter(
            Q(order_number__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    if date_from:
        orders_list = orders_list.filter(created_at__date__gte=date_from)
    
    if date_to:
        orders_list = orders_list.filter(created_at__date__lte=date_to)
    
    # Pagination
    paginator = Paginator(orders_list.order_by('-created_at'), 10)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    context = {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'admin/orders.html', context)

@login_required
@user_passes_test(is_admin)
def categories(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        image = request.FILES.get('image')
        
        if name:
            category = Category.objects.create(
                name=name,
                description=description,
                image=image if image else None
            )
            messages.success(request, f'Category "{category.name}" created successfully!')
            return redirect('admin_dashboard:categories')
        else:
            messages.error(request, 'Category name is required.')
    
    # Get all categories with product count
    categories_list = Category.objects.annotate(
        product_count=Count('product', filter=Q(product__is_approved=True))
    ).order_by('name')
    
    return render(request, 'admin/categories.html', {
        'categories': categories_list
    })

@login_required
@user_passes_test(is_admin)
def edit_category(request, category_id):
    try:
        category = Category.objects.get(id=category_id)
        if request.method == 'POST':
            category.name = request.POST.get('name')
            category.description = request.POST.get('description')
            if 'image' in request.FILES:
                category.image = request.FILES['image']
            category.save()
            messages.success(request, f'Category "{category.name}" updated successfully!')
            return redirect('admin_dashboard:categories')
        return JsonResponse({
            'id': category.id,
            'name': category.name,
            'description': category.description or '',
            'image_url': category.image.url if category.image else ''
        })
    except Category.DoesNotExist:
        messages.error(request, 'Category not found.')
        return redirect('admin_dashboard:categories')
    except Exception as e:
        messages.error(request, f'Error updating category: {str(e)}')
        return redirect('admin_dashboard:categories')

@login_required
@user_passes_test(is_admin)
def delete_category(request, category_id):
    if request.method == 'POST':
        try:
            category = Category.objects.get(id=category_id)
            name = category.name
            if category.product_set.exists():
                messages.error(request, f'Cannot delete category "{name}" as it has associated products.')
            else:
                category.delete()
                messages.success(request, f'Category "{name}" deleted successfully!')
            return redirect('admin_dashboard:categories')
        except Category.DoesNotExist:
            messages.error(request, 'Category not found.')
        except Exception as e:
            messages.error(request, f'Error deleting category: {str(e)}')
    return redirect('admin_dashboard:categories')

@login_required
@user_passes_test(is_admin)
def reports(request):
    # Get date range
    end_date = timezone.now()
    start_date = end_date - timezone.timedelta(days=30)  # Default to last 30 days
    
    if request.GET.get('start_date'):
        start_date = timezone.datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d')
    if request.GET.get('end_date'):
        end_date = timezone.datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d')
    
    # Sales Statistics
    total_sales = Order.objects.filter(
        status='DELIVERED',
        created_at__date__range=[start_date, end_date]
    ).aggregate(
        total_amount=Sum('total'),
        total_orders=Count('id')
    )
    
    # Calculate average order value
    average_order_value = 0
    if total_sales['total_orders'] > 0:
        average_order_value = total_sales['total_amount'] / total_sales['total_orders']
    
    # Total products sold and new buyers
    total_products_sold = OrderItem.objects.filter(
        order__status='DELIVERED',
        order__created_at__date__range=[start_date, end_date]
    ).aggregate(
        total_quantity=Sum('quantity')
    )['total_quantity'] or 0
    
    new_buyers = User.objects.filter(
        role='BUYER',
        date_joined__date__range=[start_date, end_date]
    ).count()
    
    # Sales Trend Data (daily)
    sales_data = []
    sales_labels = []
    for i in range(30):
        date = end_date - timezone.timedelta(days=i)
        amount = Order.objects.filter(
            created_at__date=date.date(),
            status='DELIVERED'
        ).aggregate(Sum('total'))['total__sum'] or 0
        sales_data.insert(0, float(amount))
        sales_labels.insert(0, date.strftime('%b %d'))
    
    # Category Distribution
    categories = Category.objects.annotate(
        total_sales=Sum(
            'product__order_items__total',
            filter=Q(
                product__order_items__order__status='DELIVERED',
                product__order_items__order__created_at__date__range=[start_date, end_date]
            )
        )
    ).order_by('-total_sales')[:5]
    
    category_labels = [cat.name for cat in categories]
    category_data = [float(cat.total_sales or 0) for cat in categories]
    
    # Top Products
    top_products = Product.objects.filter(
        order_items__order__status='DELIVERED',
        order_items__order__created_at__date__range=[start_date, end_date]
    ).annotate(
        total_sales=Sum('order_items__total')
    ).order_by('-total_sales')[:5]
    
    top_products_labels = [product.name for product in top_products]
    top_products_data = [float(product.total_sales or 0) for product in top_products]
    
    # Seller Performance
    top_sellers = User.objects.filter(
        role='SELLER',
        product__order_items__order__status='DELIVERED',
        product__order_items__order__created_at__date__range=[start_date, end_date]
    ).annotate(
        total_sales=Sum('product__order_items__total')
    ).order_by('-total_sales')[:5]
    
    seller_labels = [seller.get_full_name() or seller.email for seller in top_sellers]
    seller_data = [float(seller.total_sales or 0) for seller in top_sellers]
    
    # Daily Sales Comparison
    current_period = []
    previous_period = []
    daily_comparison_labels = []
    
    for i in range(7):  # Last 7 days
        current_date = end_date - timezone.timedelta(days=i)
        previous_date = current_date - timezone.timedelta(days=7)
        
        current_amount = Order.objects.filter(
            created_at__date=current_date.date(),
            status='DELIVERED'
        ).aggregate(Sum('total'))['total__sum'] or 0
        
        previous_amount = Order.objects.filter(
            created_at__date=previous_date.date(),
            status='DELIVERED'
        ).aggregate(Sum('total'))['total__sum'] or 0
        
        current_period.insert(0, float(current_amount))
        previous_period.insert(0, float(previous_amount))
        daily_comparison_labels.insert(0, current_date.strftime('%a'))
    
    # Order Status Distribution
    order_status_counts = Order.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    order_status_labels = [status['status'] for status in order_status_counts]
    order_status_data = [status['count'] for status in order_status_counts]
    
    context = {
        'start_date': start_date.date(),
        'end_date': end_date.date(),
        'total_sales': total_sales,
        'average_order_value': average_order_value,
        'total_products_sold': total_products_sold,
        'new_buyers': new_buyers,
        'sales_labels': json.dumps(sales_labels),
        'sales_data': json.dumps(sales_data),
        'category_labels': json.dumps(category_labels),
        'category_data': json.dumps(category_data),
        'top_products_labels': json.dumps(top_products_labels),
        'top_products_data': json.dumps(top_products_data),
        'seller_labels': json.dumps(seller_labels),
        'seller_data': json.dumps(seller_data),
        'daily_comparison_labels': json.dumps(daily_comparison_labels),
        'daily_comparison_current': json.dumps(current_period),
        'daily_comparison_previous': json.dumps(previous_period),
        'order_status_labels': json.dumps(order_status_labels),
        'order_status_data': json.dumps(order_status_data),
    }
    
    return render(request, 'admin/reports.html', context)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_http_methods(['POST'])
def approve_product(request, product_id):
    """Approve a pending product."""
    try:
        product = get_object_or_404(Product, id=product_id)
        
        # Check if product is already approved
        if product.is_approved:
            return JsonResponse({
                'status': 'error',
                'message': 'Product is already approved'
            }, status=400)
        
        # Approve the product
        product.is_approved = True
        product.save()
        
        messages.success(request, f'Product "{product.name}" has been approved.')
        
        return JsonResponse({
            'status': 'success',
            'message': f'Product "{product.name}" has been approved successfully.',
            'product_id': product_id
        })
    except Product.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': f'Product with ID {product_id} not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
@require_http_methods(["POST"])
def reject_product(request, product_id):
    """Reject a pending product."""
    try:
        print(f"Rejecting product {product_id}")
        print("Request body:", request.body.decode('utf-8'))
        
        product = get_object_or_404(Product, id=product_id)
        
        # Check if product is already rejected
        if not product.is_approved and product.rejection_reason:
            return JsonResponse({
                'status': 'error',
                'message': 'Product is already rejected'
            }, status=400)
        
        # Get rejection reason from request
        try:
            data = json.loads(request.body)
            reason = data.get('reason', '')
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)
        
        if not reason:
            return JsonResponse({
                'status': 'error',
                'message': 'Rejection reason is required'
            }, status=400)
        
        print(f"Rejection reason: {reason}")
        
        # Reject the product
        product.is_approved = False
        product.rejection_reason = reason
        product.save()
        
        print(f"Product {product_id} rejected successfully")
        
        # Send notification to seller (you can implement this later)
        messages.success(request, f'Product "{product.name}" has been rejected.')
        
        return JsonResponse({
            'status': 'success',
            'message': f'Product "{product.name}" has been rejected successfully.',
            'product_id': product_id
        })
    except Product.DoesNotExist:
        print(f"Product {product_id} not found")
        return JsonResponse({
            'status': 'error',
            'message': 'Product not found'
        }, status=404)
    except Exception as e:
        print(f"Error rejecting product {product_id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
def stock_overview(request):
    # Get stock statistics
    total_products = Product.objects.count()
    in_stock_products = Product.objects.filter(stock_quantity__gt=0).count()
    low_stock_products = Product.objects.filter(
        stock_alert__isnull=False,
        stock_quantity__lte=F('stock_alert__threshold_quantity')
    ).count()
    out_of_stock_products = Product.objects.filter(stock_quantity=0).count()
    
    # Get low stock alerts
    low_stock_alerts = StockAlert.objects.select_related('product', 'product__seller').filter(
        is_active=True,
        product__stock_quantity__lte=F('threshold_quantity')
    ).order_by('product__stock_quantity')
    
    # Get recent stock history
    recent_stock_history = StockHistory.objects.select_related(
        'product', 'product__seller', 'changed_by'
    ).order_by('-created_at')[:20]
    
    context = {
        'total_products': total_products,
        'in_stock_products': in_stock_products,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'low_stock_alerts': low_stock_alerts,
        'recent_stock_history': recent_stock_history,
    }
    
    return render(request, 'admin_dashboard/stock_overview.html', context)

@login_required
@user_passes_test(is_admin)
def stock_alerts(request):
    alerts = StockAlert.objects.select_related('product', 'product__seller').all()
    
    # Filter alerts
    filter_status = request.GET.get('status')
    if filter_status == 'active':
        alerts = alerts.filter(is_active=True)
    elif filter_status == 'inactive':
        alerts = alerts.filter(is_active=False)
    
    # Search alerts
    search_query = request.GET.get('q')
    if search_query:
        alerts = alerts.filter(
            Q(product__name__icontains=search_query) |
            Q(product__seller__email__icontains=search_query)
        )
    
    # Paginate alerts
    paginator = Paginator(alerts, 20)
    page = request.GET.get('page')
    alerts = paginator.get_page(page)
    
    context = {
        'alerts': alerts,
        'filter_status': filter_status,
        'search_query': search_query,
    }
    
    return render(request, 'admin_dashboard/stock_alerts.html', context)

@login_required
@user_passes_test(is_admin)
def stock_history(request):
    history = StockHistory.objects.select_related(
        'product', 'product__seller', 'changed_by'
    ).all()
    
    # Filter by change type
    change_type = request.GET.get('type')
    if change_type:
        history = history.filter(change_type=change_type)
    
    # Filter by date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date and end_date:
        history = history.filter(created_at__date__range=[start_date, end_date])
    
    # Search history
    search_query = request.GET.get('q')
    if search_query:
        history = history.filter(
            Q(product__name__icontains=search_query) |
            Q(product__seller__email__icontains=search_query) |
            Q(change_reason__icontains=search_query)
        )
    
    # Paginate history
    paginator = Paginator(history.order_by('-created_at'), 50)
    page = request.GET.get('page')
    history = paginator.get_page(page)
    
    context = {
        'history': history,
        'change_type': change_type,
        'start_date': start_date,
        'end_date': end_date,
        'search_query': search_query,
        'change_types': StockHistory.STOCK_CHANGE_TYPES,
    }
    
    return render(request, 'admin_dashboard/stock_history.html', context)

@login_required
@user_passes_test(is_admin)
def order_detail(request, order_id):
    """API endpoint to get order details"""
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Prepare order items data
        items_data = []
        for item in order.order_items.select_related('product').all():
            items_data.append({
                'name': item.product.name,
                'quantity': item.quantity,
                'price': item.price_per_kg,
                'total': item.total
            })
        
        # Prepare user data
        user_data = {
            'first_name': order.user.first_name or '',
            'last_name': order.user.last_name or '',
            'email': order.user.email,
            'phone': order.user.phone or '',
            'company_name': getattr(order.user, 'company_name', '') or '',
            'gst_number': getattr(order.user, 'gst_number', '') or ''
        }
        
        # Prepare shipment data if exists
        shipment_data = None
        if hasattr(order, 'shipment'):
            shipment_data = {
                'tracking_number': order.shipment.tracking_number,
                'carrier': order.shipment.carrier,
                'estimated_delivery': order.shipment.estimated_delivery.isoformat() if order.shipment.estimated_delivery else None,
                'status': order.shipment.status
            }
        
        # Prepare response data
        data = {
            'id': order.id,
            'order_number': order.order_number,
            'created_at': order.created_at.isoformat(),
            'status': order.status,
            'payment_status': order.payment_status,
            'total': str(order.total),  # Convert Decimal to string
            'user': user_data,
            'items': items_data,
            'shipment': shipment_data
        }
        
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Failed to load order details'
        }, status=500)

@login_required
@user_passes_test(is_admin)
def update_user(request, user_id):
    """Update user information."""
    if request.method not in ['GET', 'POST']:
        return JsonResponse({
            'status': 'error',
            'message': 'Method not allowed'
        }, status=405)

    try:
        user = get_object_or_404(User, id=user_id)
        
        if request.method == 'GET':
            return JsonResponse({
                'status': 'success',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'is_active': user.is_active,
                    'phone': str(user.phone) if user.phone else ''
                }
            })
        
        elif request.method == 'POST':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid JSON data'
                }, status=400)
            
            # Update basic info
            if 'first_name' in data:
                user.first_name = data['first_name']
            if 'last_name' in data:
                user.last_name = data['last_name']
            if 'email' in data:
                user.email = data['email']
            if 'phone' in data:
                user.phone = data['phone']
            
            # Update role if provided and different
            if 'role' in data:
                new_role = data['role']
                if new_role not in ['ADMIN', 'SELLER', 'CUSTOMER']:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Invalid role specified'
                    }, status=400)
                user.role = new_role
            
            # Update status
            if 'is_active' in data:
                user.is_active = data['is_active']
            
            try:
                user.save()
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Error saving user: {str(e)}'
                }, status=500)
            
            return JsonResponse({
                'status': 'success',
                'message': f'User {user.get_full_name() or user.email} updated successfully',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'is_active': user.is_active,
                    'phone': str(user.phone) if user.phone else ''
                }
            })
    
    except User.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'User not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }, status=500)

@login_required
@user_passes_test(is_admin)
def delete_user(request, user_id):
    """Delete a user."""
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Starting delete_user for user_id: {user_id}")
    
    if request.method != 'POST':
        logger.error(f"Method not allowed: {request.method}")
        return JsonResponse({
            'status': 'error',
            'message': 'Method not allowed'
        }, status=405)
    
    try:
        logger.error(f"Attempting to get user with id: {user_id}")
        user = User.objects.select_for_update().get(id=user_id)
        
        # Don't allow deleting yourself
        if user.id == request.user.id:
            logger.error(f"User attempted to delete themselves: {user_id}")
            return JsonResponse({
                'status': 'error',
                'message': 'You cannot delete your own account'
            }, status=403)
        
        # Store the name for the success message
        user_name = user.get_full_name() or user.email
        logger.error(f"Found user to delete: {user_name}")
        
        try:
            with transaction.atomic():
                # Instead of checking for related objects, we'll just soft delete
                user.is_deleted = True
                user.is_active = False  # This will prevent login
                user.save()
                
                logger.error(f"Successfully soft deleted user {user_id}")
                
                return JsonResponse({
                    'status': 'success',
                    'message': f'User {user_name} has been deleted successfully',
                    'user_id': user_id
                })
        except Exception as e:
            error_msg = f"Error soft deleting user {user_id}: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return JsonResponse({
                'status': 'error',
                'message': f'Error deleting user: {str(e)}'
            }, status=500)
            
    except User.DoesNotExist:
        error_msg = f"User not found: {user_id}"
        logger.error(error_msg)
        return JsonResponse({
            'status': 'error',
            'message': 'User not found'
        }, status=404)
    except Exception as e:
        error_msg = f"Unexpected error for user {user_id}: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return JsonResponse({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }, status=500)
