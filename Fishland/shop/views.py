from django.shortcuts import render
from django.core.paginator import Paginator

def home(request):
    return render(request, 'shop/home.html')

def about(request):
    return render(request, 'shop/about.html')

def contact(request):
    return render(request, 'shop/contact.html')

def products(request):
    # Dummy data for now - we'll replace this with database queries later
    categories = [
        {'id': 1, 'name': 'Fresh Fish'},
        {'id': 2, 'name': 'Shellfish'},
        {'id': 3, 'name': 'Dried Fish'},
        {'id': 4, 'name': 'Crustaceans'},
    ]
    
    products = [
        {
            'id': 1,
            'name': 'Fresh Pomfret',
            'description': 'Fresh white pomfret, perfect for frying',
            'price': 800,
            'image': 'images/products/pomfret.jpg',
            'category_id': 1,
            'stock': 50,
            'unit': 'kg'
        },
        {
            'id': 2,
            'name': 'King Prawns',
            'description': 'Large king prawns, ideal for curries',
            'price': 1200,
            'image': 'images/products/prawns.jpg',
            'category_id': 2,
            'stock': 30,
            'unit': 'kg'
        },
        {
            'id': 3,
            'name': 'Bombay Duck',
            'description': 'Dried Bombay duck, ready to cook',
            'price': 400,
            'image': 'images/products/bombay-duck.jpg',
            'category_id': 3,
            'stock': 100,
            'unit': 'kg'
        },
    ]
    
    # Get filter parameters
    selected_categories = request.GET.getlist('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    # Filter products (basic filtering for now)
    if selected_categories:
        products = [p for p in products if str(p['category_id']) in selected_categories]
    if min_price:
        products = [p for p in products if p['price'] >= float(min_price)]
    if max_price:
        products = [p for p in products if p['price'] <= float(max_price)]
    
    # Pagination
    paginator = Paginator(products, 12)  # 12 products per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'categories': categories,
        'products': page_obj,
    }
    return render(request, 'shop/products.html', context)

def delivery(request):
    # For now, just render the template without any delivery areas
    # We'll add delivery area functionality later
    return render(request, 'shop/delivery.html')
