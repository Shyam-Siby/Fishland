from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from .models import Product, Category, ProductReview
from orders.models import OrderReview, OrderItem
from django.db.models import Prefetch

def product_list(request):
    """Display all approved and available products."""
    products = Product.objects.filter(is_approved=True, is_available=True).order_by('-created_at')
    
    # Handle search
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )
    
    # Handle category filter
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Handle sorting
    sort_by = request.GET.get('sort')
    if sort_by == 'price_low':
        products = products.order_by('price_per_kg')
    elif sort_by == 'price_high':
        products = products.order_by('-price_per_kg')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)  # Show 12 products per page
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    # Get all categories for filter sidebar
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
        'current_category': category_id,
        'current_sort': sort_by,
        'search_query': query
    }
    return render(request, 'products/product_list.html', context)

def product_detail(request, product_id):
    """Display detailed information about a specific product."""
    product = get_object_or_404(Product, id=product_id, is_approved=True)
    
    # Get order items for this product that have been delivered and have reviews
    order_items = OrderItem.objects.filter(
        product=product,
        order__status='DELIVERED'
    ).select_related('order__review', 'order__user')
    
    # Get reviews from delivered orders
    reviews = []
    for item in order_items:
        if hasattr(item.order, 'review'):
            review = item.order.review
            reviews.append({
                'rating': review.rating,
                'comment': review.comment,
                'user': review.user,
                'created_at': review.created_at,
                'order': item.order
            })
    
    # Calculate average rating
    if reviews:
        avg_rating = sum(review['rating'] for review in reviews) / len(reviews)
    else:
        avg_rating = None
    
    # Check if user can review (has ordered and received but not reviewed)
    can_review = False
    if request.user.is_authenticated:
        delivered_orders = OrderItem.objects.filter(
            product=product,
            order__user=request.user,
            order__status='DELIVERED'
        ).exclude(order__review__isnull=False).exists()
        can_review = delivered_orders
    
    # Sort reviews by date
    reviews.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Get related products
    related_products = Product.objects.filter(
        category=product.category,
        is_approved=True,
        is_available=True
    ).exclude(id=product.id)[:4]
    
    context = {
        'product': product,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'review_count': len(reviews),
        'can_review': can_review,
        'related_products': related_products
    }
    return render(request, 'products/product_detail.html', context)

def category_list(request):
    """Display all product categories."""
    categories = Category.objects.all()
    return render(request, 'products/category_list.html', {'categories': categories})

def category_detail(request, category_id):
    """Display products in a specific category."""
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(
        category=category,
        is_approved=True,
        is_available=True
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    context = {
        'category': category,
        'products': products
    }
    return render(request, 'products/category_detail.html', context)

@login_required
def add_review(request, product_id):
    """Add a review to a product."""
    product = get_object_or_404(Product, id=product_id, is_approved=True)
    
    if request.method == 'POST':
        form = ProductReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            return redirect('product_detail', product_id=product_id)
    
    return redirect('product_detail', product_id=product_id)
