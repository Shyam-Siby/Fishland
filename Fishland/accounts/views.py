from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.views import (
    PasswordResetView, 
    PasswordResetDoneView,
    PasswordResetConfirmView, 
    PasswordResetCompleteView
)
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.decorators.csrf import csrf_protect
from .models import User, SellerProfile, BuyerProfile
from .forms import (
    UserRegistrationForm,
    UserLoginForm,
    UserUpdateForm,
    SellerRegistrationForm,
    SellerProfileUpdateForm,
    BuyerProfileUpdateForm,
    AddressForm  # Import AddressForm
)
from django.utils.text import slugify
import uuid
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from orders.models import Address, Order
from django.shortcuts import get_object_or_404  # Import get_object_or_404

def generate_unique_username(email):
    """Generate a unique username from email."""
    # Get the part before @ in email
    username = email.split('@')[0]
    # Slugify to make it URL friendly
    username = slugify(username)
    # Add random string to make it unique
    username = f"{username}-{str(uuid.uuid4())[:8]}"
    return username

@csrf_protect
def login_view(request):
    """Handle user login with email and password."""
    if request.user.is_authenticated:
        if request.user.role == User.Role.ADMIN:
            return redirect('/admin_dashboard/')  # Use absolute URL for admin dashboard
        elif request.user.role == User.Role.SELLER:
            return redirect('seller:dashboard')
        elif request.user.role == User.Role.DELIVERY_BOY:
            return redirect('delivery:dashboard')
        else:
            return redirect('shop:home')

    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(request, email=email, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.email}!')
                
                # Redirect based on user role
                if user.role == User.Role.ADMIN:
                    return redirect('/admin_dashboard/')  # Use absolute URL for admin dashboard
                elif user.role == User.Role.SELLER:
                    return redirect('seller:dashboard')
                elif user.role == User.Role.DELIVERY_BOY:
                    return redirect('delivery:dashboard')
                else:
                    next_url = request.GET.get('next')
                    if next_url:
                        return redirect(next_url)
                    return redirect('shop:home')
            else:
                messages.error(request, 'Invalid email or password.')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

@csrf_protect
def register_view(request):
    """Handle user registration."""
    if request.user.is_authenticated:
        return redirect('shop:home')
        
    if request.method == 'POST':
        account_type = request.POST.get('account_type')
        
        if account_type == 'seller':
            form = SellerRegistrationForm(request.POST, request.FILES)
            account_name = "Seller"
        else:
            form = UserRegistrationForm(request.POST)
            account_name = "Buyer"
            
        if form.is_valid():
            user = form.save(commit=False)
            # Generate unique username from email
            user.username = generate_unique_username(form.cleaned_data['email'])
            
            if account_type == 'seller':
                user.role = User.Role.SELLER
                user.company_name = form.cleaned_data['company_name']
                user.gst_number = form.cleaned_data['gst_number']
                user.save()
                
                # Create seller profile
                SellerProfile.objects.create(
                    user=user,
                    business_license=form.cleaned_data.get('business_license'),
                )
            else:
                user.role = User.Role.BUYER
                user.save()
                
                # Create buyer profile with default values
                BuyerProfile.objects.create(
                    user=user,
                    business_type='OTHER',  # Default value
                    preferred_payment_method='BANK_TRANSFER',  # Default value
                )
            
            # Log in the user with the ModelBackend
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            messages.success(
                request, 
                f'Welcome to FISHLAND! Your {account_name} account has been created successfully.'
            )
            
            if user.is_seller:
                return redirect('seller:dashboard')
            else:
                return redirect('shop:home')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def logout_view(request):
    """Handle user logout."""
    user_role = request.user.role  # Get user role before logout
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    
    # Redirect to the appropriate login page based on previous role
    if user_role == User.Role.ADMIN:
        return redirect('accounts:login')  # Admin login page
    elif user_role == User.Role.DELIVERY_BOY:
        return redirect('delivery:login')  # Delivery login page
    elif user_role == User.Role.SELLER:
        return redirect('seller:login')  # Seller login page
    else:
        return redirect('accounts:login')  # Default login page

class CustomPasswordResetView(SuccessMessageMixin, PasswordResetView):
    """Custom password reset view."""
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')
    success_message = "We've emailed you instructions for setting your password."

class CustomPasswordResetDoneView(PasswordResetDoneView):
    """Custom password reset done view."""
    template_name = 'accounts/password_reset_done.html'

class CustomPasswordResetConfirmView(SuccessMessageMixin, PasswordResetConfirmView):
    """Custom password reset confirm view."""
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')
    success_message = "Your password has been set successfully!"

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    """Custom password reset complete view."""
    template_name = 'accounts/password_reset_complete.html'

@login_required
def profile_view(request):
    """Display and update user profile."""
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        
        if request.user.is_seller:
            profile_form = SellerProfileUpdateForm(
                request.POST, 
                request.FILES, 
                instance=request.user.seller_profile
            )
        else:
            profile_form = BuyerProfileUpdateForm(
                request.POST,
                instance=request.user.buyer_profile
            )
            
        if user_form.is_valid() and profile_form.is_valid():
            # Save user form with profile picture
            user = user_form.save(commit=False)
            if 'profile_picture' in request.FILES:
                user.profile_picture = request.FILES['profile_picture']
            user.save()
            
            # Save profile form
            profile_form.save()
            
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('accounts:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        if request.user.is_seller:
            profile_form = SellerProfileUpdateForm(instance=request.user.seller_profile)
        else:
            profile_form = BuyerProfileUpdateForm(instance=request.user.buyer_profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, 'Address added successfully!')
            return redirect('accounts:address_list')
    else:
        form = AddressForm()
    
    return render(request, 'accounts/add_address.html', {
        'form': form,
        'title': 'Add New Address',
        'button_text': 'Add Address'
    })

@login_required
def address_list(request):
    addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-created_at')
    context = {
        'addresses': addresses
    }
    return render(request, 'accounts/address_list.html', context)

@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, 'Address updated successfully!')
            return redirect('accounts:address_list')
    else:
        form = AddressForm(instance=address)
    
    return render(request, 'accounts/add_address.html', {
        'form': form,
        'title': 'Edit Address',
        'button_text': 'Update Address'
    })

@login_required
def delete_address(request, address_id):
    if request.method == 'POST':
        address = get_object_or_404(Address, id=address_id, user=request.user)
        if not address.is_default:
            address.delete()
            messages.success(request, 'Address deleted successfully!')
        else:
            messages.error(request, 'Cannot delete default address!')
    return redirect('accounts:address_list')

@login_required
def set_default_address(request, address_id):
    if request.method == 'POST':
        address = get_object_or_404(Address, id=address_id, user=request.user)
        # Remove default status from all other addresses
        Address.objects.filter(user=request.user).update(is_default=False)
        # Set this address as default
        address.is_default = True
        address.save()
        messages.success(request, 'Default address updated successfully!')
    return redirect('accounts:address_list')

# Social Authentication Views
def google_login(request):
    """Handle Google OAuth login."""
    pass  # Implement Google OAuth logic

def facebook_login(request):
    """Handle Facebook OAuth login."""
    pass  # Implement Facebook OAuth logic

def apple_login(request):
    """Handle Apple OAuth login."""
    pass  # Implement Apple OAuth logic
