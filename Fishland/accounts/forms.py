from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.validators import RegexValidator
from allauth.account.forms import SignupForm
from .models import User, SellerProfile, BuyerProfile
from orders.models import Address

class UserRegistrationForm(UserCreationForm):
    """Form for user registration."""
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        })
    )
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    phone = forms.CharField(
        validators=[phone_regex],
        max_length=17,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your phone number'
        })
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    )
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone', 'password1', 'password2')
    
    def clean_email(self):
        """Validate that the email is unique."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address is already in use.')
        return email

class CustomSignupForm(SignupForm):
    """Custom signup form for allauth."""
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        })
    )
    phone = forms.CharField(
        validators=[phone_regex],
        max_length=17,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your phone number'
        })
    )
    
    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone = self.cleaned_data['phone']
        user.save()
        return user

class SellerRegistrationForm(UserRegistrationForm):
    """Form for seller registration with additional fields."""
    company_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your company name'
        })
    )
    gst_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your GST number'
        })
    )
    business_license = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    class Meta(UserRegistrationForm.Meta):
        model = User
        fields = UserRegistrationForm.Meta.fields + ('company_name', 'gst_number', 'business_license')
    
    def save(self, commit=True):
        """Save the seller with role set to SELLER."""
        user = super().save(commit=False)
        user.role = User.Role.SELLER
        if commit:
            user.save()
            SellerProfile.objects.create(
                user=user,
                business_license=self.cleaned_data.get('business_license'),
                bank_account_number=self.cleaned_data.get('bank_account_number'),
                bank_ifsc=self.cleaned_data.get('bank_ifsc')
            )
        return user

class UserLoginForm(forms.Form):
    """Form for user login."""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )
    remember = forms.BooleanField(required=False)

class UserUpdateForm(forms.ModelForm):
    """Form for updating user profile."""
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone', 'profile_picture')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }

class SellerProfileUpdateForm(forms.ModelForm):
    """Form for updating seller profile."""
    class Meta:
        model = SellerProfile
        fields = ('business_name', 'business_description', 'gst_number', 'business_license_number')
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'gst_number': forms.TextInput(attrs={'class': 'form-control'}),
            'business_license_number': forms.TextInput(attrs={'class': 'form-control'})
        }

class BuyerProfileUpdateForm(forms.ModelForm):
    """Form for updating buyer profile."""
    class Meta:
        model = BuyerProfile
        fields = ('shipping_address', 'city', 'state', 'postal_code', 'business_type', 'preferred_payment_method')
        widgets = {
            'shipping_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'business_type': forms.Select(attrs={'class': 'form-select'}),
            'preferred_payment_method': forms.Select(attrs={'class': 'form-select'})
        }

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            'label',
            'name',
            'phone',
            'address_line1',
            'address_line2',
            'city',
            'state',
            'pincode',
            'is_default'
        ]
        widgets = {
            'label': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            'label': 'Address Label (e.g., Home, Office)',
            'name': 'Full Name',
            'phone': 'Phone Number',
            'address_line1': 'Street Address',
            'address_line2': 'Apartment, Suite, etc. (optional)',
            'pincode': 'PIN Code'
        }
