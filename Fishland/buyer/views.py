from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from orders.models import Order, OrderItem, Address, OrderReview
from products.models import Product

@login_required
def dashboard(request):
    # Get recent orders
    recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Get default address
    default_address = Address.objects.filter(user=request.user, is_default=True).first()
    
    context = {
        'recent_orders': recent_orders,
        'default_address': default_address,
    }
    return render(request, 'buyer/dashboard.html', context)

@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'buyer/orders.html', {'orders': orders})

@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    can_review = order.status == 'DELIVERED' and not order.has_review
    return render(request, 'buyer/order_detail.html', {
        'order': order,
        'can_review': can_review
    })

@login_required
def order_review(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Check if order can be reviewed
    if order.status != 'DELIVERED':
        messages.error(request, 'Only delivered orders can be reviewed.')
        return redirect('buyer:order_detail', order_number=order.order_number)
    
    if order.has_review:
        messages.error(request, 'You have already reviewed this order.')
        return redirect('buyer:order_detail', order_number=order.order_number)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        if not rating or not comment:
            messages.error(request, 'Both rating and comment are required.')
            return render(request, 'buyer/order_review.html', {'order': order})
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError('Invalid rating')
            
            review = OrderReview.objects.create(
                order=order,
                user=request.user,
                rating=rating,
                comment=comment
            )
            messages.success(request, 'Thank you for your review!')
            return redirect('buyer:order_detail', order_number=order.order_number)
            
        except ValueError:
            messages.error(request, 'Invalid rating value.')
            return render(request, 'buyer/order_review.html', {'order': order})
    
    return render(request, 'buyer/order_review.html', {'order': order})

@login_required
def edit_review(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    review = get_object_or_404(OrderReview, order=order, user=request.user)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        if not rating or not comment:
            messages.error(request, 'Both rating and comment are required.')
            return render(request, 'buyer/edit_review.html', {'order': order, 'review': review})
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError('Invalid rating')
            
            review.rating = rating
            review.comment = comment
            review.save()
            
            messages.success(request, 'Your review has been updated!')
            return redirect('buyer:order_detail', order_number=order.order_number)
            
        except ValueError:
            messages.error(request, 'Invalid rating value.')
            return render(request, 'buyer/edit_review.html', {'order': order, 'review': review})
    
    return render(request, 'buyer/edit_review.html', {'order': order, 'review': review})

@login_required
def addresses(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'buyer/addresses.html', {'addresses': addresses})

@login_required
def add_address(request):
    if request.method == 'POST':
        # Get form data
        label = request.POST.get('label')
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        address_line1 = request.POST.get('address_line1')
        address_line2 = request.POST.get('address_line2', '')
        city = request.POST.get('city')
        state = request.POST.get('state')
        pincode = request.POST.get('pincode')
        is_default = request.POST.get('is_default') == 'on'
        
        # Create new address
        address = Address.objects.create(
            user=request.user,
            label=label,
            name=name,
            phone=phone,
            address_line1=address_line1,
            address_line2=address_line2,
            city=city,
            state=state,
            pincode=pincode,
            is_default=is_default
        )
        
        messages.success(request, 'Address added successfully!')
        return redirect('buyer:addresses')
    
    return render(request, 'buyer/add_address.html')

@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        # Update address fields
        address.label = request.POST.get('label')
        address.name = request.POST.get('name')
        address.phone = request.POST.get('phone')
        address.address_line1 = request.POST.get('address_line1')
        address.address_line2 = request.POST.get('address_line2', '')
        address.city = request.POST.get('city')
        address.state = request.POST.get('state')
        address.pincode = request.POST.get('pincode')
        address.is_default = request.POST.get('is_default') == 'on'
        address.save()
        
        messages.success(request, 'Address updated successfully!')
        return redirect('buyer:addresses')
    
    return render(request, 'buyer/edit_address.html', {'address': address})

@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Address deleted successfully!')
        return redirect('buyer:addresses')
    
    return render(request, 'buyer/delete_address.html', {'address': address})

@login_required
def make_default_address(request, address_id):
    if request.method == 'POST':
        address = get_object_or_404(Address, id=address_id, user=request.user)
        
        # Remove default status from other addresses
        Address.objects.filter(user=request.user).update(is_default=False)
        
        # Set this address as default
        address.is_default = True
        address.save()
        
        messages.success(request, f'{address.label} is now your default address.')
        return redirect('buyer:addresses')
    
    return JsonResponse({'success': False}, status=405)

@login_required
def cancel_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    if order.status not in ['PENDING', 'CONFIRMED']:
        messages.error(request, 'This order cannot be cancelled.')
        return redirect('buyer:order_detail', order_number=order.order_number)
    
    if request.method == 'POST':
        order.status = 'CANCELLED'
        order.cancelled_at = timezone.now()
        order.save()
        messages.success(request, 'Order cancelled successfully.')
        return redirect('buyer:order_detail', order_number=order.order_number)
    
    return render(request, 'buyer/cancel_order.html', {'order': order})
