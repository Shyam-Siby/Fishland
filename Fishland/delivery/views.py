from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.utils import timezone
import json

from .models import DeliveryProfile
from accounts.models import User
from orders.models import Order

def is_delivery_boy(user):
    return user.is_authenticated and user.role == User.Role.DELIVERY_BOY

def delivery_register(request):
    if request.method == 'POST':
        # Get form data
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone')
        vehicle_type = request.POST.get('vehicle_type')
        vehicle_number = request.POST.get('vehicle_number')
        license_number = request.POST.get('license_number')
        license_image = request.FILES.get('license_image')
        
        # Validate required fields
        required_fields = {
            'email': email,
            'password': password,
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'vehicle_type': vehicle_type,
            'vehicle_number': vehicle_number,
            'license_number': license_number,
            'license_image': license_image
        }
        
        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            messages.error(request, f'Please fill in all required fields: {", ".join(missing_fields)}')
            return redirect('delivery:register')
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('delivery:register')
        
        # Generate username from email
        username = email.split('@')[0]
        base_username = username
        counter = 1
        # Make sure username is unique
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        user = None
        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=User.Role.DELIVERY_BOY
            )
            
            # Create delivery profile
            DeliveryProfile.objects.create(
                user=user,
                phone=phone,
                vehicle_type=vehicle_type,
                vehicle_number=vehicle_number,
                license_number=license_number,
                license_image=license_image,
                status='OFFLINE',
                is_active=True
            )
            
            messages.success(request, 'Registration successful! Please login.')
            return redirect('delivery:login')
            
        except Exception as e:
            if user:
                user.delete()  # Rollback user creation if profile creation fails
            messages.error(request, f'Error creating account: {str(e)}')
            return redirect('delivery:register')
    
    return render(request, 'delivery/register.html', {
        'vehicle_types': DeliveryProfile.VEHICLE_TYPES
    })

def delivery_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, email=email, password=password)
        
        if user is not None and user.role == User.Role.DELIVERY_BOY:
            if hasattr(user, 'delivery_profile'):
                if user.delivery_profile.is_active:
                    login(request, user)
                    messages.success(request, 'Welcome back!')
                    return redirect('delivery:dashboard')
                else:
                    messages.error(request, 'Your account is currently inactive. Please contact support.')
            else:
                messages.error(request, 'Delivery profile not found. Please contact support.')
        else:
            messages.error(request, 'Invalid email or password.')
    
    return render(request, 'delivery/login.html')

@login_required
@user_passes_test(is_delivery_boy)
def dashboard(request):
    """Delivery agent dashboard view."""
    delivery_profile = request.user.delivery_profile
    
    # Get current orders
    current_orders = Order.objects.filter(
        delivery_boy=delivery_profile,
        status__in=['READY_FOR_DELIVERY', 'ASSIGNED_TO_DELIVERY', 'ACCEPTED', 'OUT_FOR_DELIVERY']
    ).order_by('-created_at')
    
    # Get completed orders count
    completed_orders_count = Order.objects.filter(
        delivery_boy=delivery_profile,
        status='DELIVERED'
    ).count()
    
    # Get today's earnings
    today = timezone.now().date()
    today_earnings = Order.objects.filter(
        delivery_boy=delivery_profile,
        status='DELIVERED',
        delivered_at__date=today
    ).aggregate(total=Sum('delivery_fee'))['total'] or 0
    
    context = {
        'current_orders': current_orders,
        'completed_orders_count': completed_orders_count,
        'today_earnings': today_earnings,
        'delivery_profile': delivery_profile
    }
    
    return render(request, 'delivery/dashboard.html', context)

@login_required
@user_passes_test(is_delivery_boy)
def orders(request):
    """View for managing current orders."""
    delivery_profile = request.user.delivery_profile
    current_orders = Order.objects.filter(
        delivery_boy=delivery_profile,
        status__in=['READY_FOR_DELIVERY', 'ASSIGNED_TO_DELIVERY', 'ACCEPTED', 'OUT_FOR_DELIVERY']
    ).order_by('-created_at')
    
    return render(request, 'delivery/orders.html', {'orders': current_orders})

@login_required
@user_passes_test(is_delivery_boy)
def history(request):
    """View delivery history."""
    delivery_profile = request.user.delivery_profile
    completed_orders = Order.objects.filter(
        delivery_boy=delivery_profile,
        status='DELIVERED'
    ).order_by('-delivered_at')
    
    return render(request, 'delivery/history.html', {'orders': completed_orders})

@login_required
@user_passes_test(is_delivery_boy)
def earnings(request):
    """View earnings details."""
    delivery_profile = request.user.delivery_profile
    
    # Get earnings for different time periods
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Calculate earnings
    today_earnings = Order.objects.filter(
        delivery_boy=delivery_profile,
        status='DELIVERED',
        delivered_at__date=today
    ).aggregate(total=Sum('delivery_fee'))['total'] or 0
    
    weekly_earnings = Order.objects.filter(
        delivery_boy=delivery_profile,
        status='DELIVERED',
        delivered_at__date__gte=week_ago
    ).aggregate(total=Sum('delivery_fee'))['total'] or 0
    
    monthly_earnings = Order.objects.filter(
        delivery_boy=delivery_profile,
        status='DELIVERED',
        delivered_at__date__gte=month_ago
    ).aggregate(total=Sum('delivery_fee'))['total'] or 0
    
    context = {
        'today_earnings': today_earnings,
        'weekly_earnings': weekly_earnings,
        'monthly_earnings': monthly_earnings,
    }
    
    return render(request, 'delivery/earnings.html', context)

@login_required
@user_passes_test(is_delivery_boy)
def order_detail(request, order_id):
    """View order details and update status."""
    delivery_profile = request.user.delivery_profile
    order = get_object_or_404(Order, id=order_id, delivery_boy=delivery_profile)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'accept':
            order.status = 'OUT_FOR_DELIVERY'
            order.delivery_pickup_at = timezone.now()
            messages.success(request, 'Order picked up successfully.')
        elif action == 'complete':
            order.status = 'DELIVERED'
            order.delivery_completed_at = timezone.now()
            messages.success(request, 'Order delivered successfully.')
        order.save()
        return redirect('delivery:orders')
    
    return render(request, 'delivery/order_detail.html', {
        'order': order
    })

@login_required
@user_passes_test(is_delivery_boy)
def update_status(request, order_id):
    """Update order status after delivery."""
    order = get_object_or_404(Order, id=order_id, delivery_boy=request.user.delivery_profile)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'deliver':
            try:
                print("\n=== Processing Delivery Completion ===")
                print(f"Order: #{order.id}")
                print(f"Previous Status: {order.status}")
                
                # Update order status
                order.status = 'DELIVERED'
                order.delivery_completed_at = timezone.now()
                
                # Unlink delivery boy and reset their status
                delivery_boy = order.delivery_boy
                order.delivery_boy = None
                order.save()
                
                print(f"New Status: {order.status}")
                print(f"Delivery Boy: {delivery_boy}")
                
                # Check if delivery boy has other pending orders
                pending_orders = Order.objects.filter(
                    delivery_boy=delivery_boy,
                    status__in=['ASSIGNED_TO_DELIVERY', 'OUT_FOR_DELIVERY']
                )
                
                if not pending_orders.exists():
                    print("No more pending orders, setting status to ONLINE")
                    delivery_boy.status = 'ONLINE'
                    delivery_boy.save()
                else:
                    print(f"Has {pending_orders.count()} more pending orders")
                    
                print("=== Delivery Completion Processed ===\n")
                
                messages.success(request, f'Order #{order.id} marked as delivered.')
                return redirect('delivery:orders')
                
            except Exception as e:
                print(f"Error in delivery completion: {str(e)}")
                messages.error(request, f'Error updating order status: {str(e)}')
                return redirect('delivery:order_detail', order_id=order.id)
    
    return redirect('delivery:order_detail', order_id=order_id)

@login_required
@user_passes_test(is_delivery_boy)
def fix_delivered_orders(request):
    """One-time fix for delivered orders that still have delivery boys linked."""
    try:
        # Get all delivered orders that still have delivery boys linked
        delivered_orders = Order.objects.filter(
            status='DELIVERED',
            delivery_boy__isnull=False
        )
        
        fixed_count = 0
        for order in delivered_orders:
            print(f"\nProcessing Order #{order.id}")
            print(f"Current Status: {order.status}")
            print(f"Delivery Boy: {order.delivery_boy}")
            
            # Get delivery boy before unlinking
            delivery_boy = order.delivery_boy
            
            # Unlink delivery boy from order
            order.delivery_boy = None
            order.save()
            
            # Check if delivery boy has other pending orders
            pending_orders = Order.objects.filter(
                delivery_boy=delivery_boy,
                status__in=['ASSIGNED_TO_DELIVERY', 'OUT_FOR_DELIVERY']
            )
            
            print(f"Pending Orders: {pending_orders.count()}")
            
            if not pending_orders.exists():
                print(f"Setting {delivery_boy} status to ONLINE")
                delivery_boy.status = 'ONLINE'
                delivery_boy.save()
            
            fixed_count += 1
            
        messages.success(request, f'Fixed {fixed_count} delivered orders.')
        
    except Exception as e:
        print(f"Error fixing orders: {str(e)}")
        messages.error(request, f'Error fixing orders: {str(e)}')
    
    return redirect('delivery:dashboard')

@login_required
@user_passes_test(is_delivery_boy)
def toggle_status(request):
    """Toggle delivery agent's online/offline status."""
    if request.method == 'POST':
        delivery_profile = request.user.delivery_profile
        
        # Handle JSON request
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                status = data.get('status')
                if status == 'AVAILABLE':
                    delivery_profile.status = 'ONLINE'
                else:
                    delivery_profile.status = 'OFFLINE'
                delivery_profile.save()
                return JsonResponse({
                    'success': True, 
                    'status': delivery_profile.status,
                    'display_status': delivery_profile.get_status_display()
                })
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        
        # Handle form submit
        else:
            current_status = delivery_profile.status
            print(f"\n=== Toggle Status Request ===")
            print(f"Current Status: {current_status}")
            
            # Check only for active pending orders
            pending_orders = Order.objects.filter(
                delivery_boy=delivery_profile,
                status__in=['ASSIGNED_TO_DELIVERY', 'OUT_FOR_DELIVERY']
            )
            print(f"Active Pending Orders: {pending_orders.count()}")
            
            if current_status == 'ONLINE':
                delivery_profile.status = 'OFFLINE'
                messages.success(request, 'You are now offline.')
            elif current_status in ['BUSY', 'ON_DELIVERY']:
                if pending_orders.exists():
                    order_list = ", ".join([f"#{order.id}" for order in pending_orders])
                    messages.error(request, f'Please complete or unassign your pending orders first: {order_list}')
                else:
                    delivery_profile.status = 'ONLINE'
                    messages.success(request, 'You are now online.')
            else:  # OFFLINE
                delivery_profile.status = 'ONLINE'
                messages.success(request, 'You are now online.')
                
            delivery_profile.save()
            print(f"New Status: {delivery_profile.status}")
            print("=== End Toggle Status ===\n")
            
            return redirect('delivery:dashboard')
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

@login_required
def profile(request):
    if request.method == 'POST':
        # Handle profile update
        profile = request.user.delivery_profile
        profile.phone = request.POST.get('phone')
        profile.vehicle_type = request.POST.get('vehicle_type')
        profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('delivery:profile')
    
    return render(request, 'delivery/profile.html', {
        'profile': request.user.delivery_profile
    })

@login_required
def settings(request):
    if request.method == 'POST':
        # Handle settings update
        profile = request.user.delivery_profile
        profile.notification_enabled = request.POST.get('notifications') == 'on'
        profile.save()
        messages.success(request, 'Settings updated successfully!')
        return redirect('delivery:settings')
    
    return render(request, 'delivery/settings.html', {
        'profile': request.user.delivery_profile
    })

@login_required
def update_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_status = data.get('status')
            
            # Validate the status
            valid_statuses = [status[0] for status in DeliveryProfile.STATUS_CHOICES]
            if new_status not in valid_statuses:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid status'
                })
            
            # Update the delivery profile
            profile = request.user.delivery_profile
            profile.status = new_status
            profile.save()
            
            return JsonResponse({
                'success': True,
                'status': profile.get_status_display()
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
            
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })
