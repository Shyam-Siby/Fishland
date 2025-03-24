from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import user_field
from django.conf import settings

class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        """
        This is called when saving user via allauth registration.
        We override this to set additional data on user object.
        """
        # Get the account type from the form
        account_type = request.POST.get('account_type', 'buyer')
        
        # Save user using allauth
        user = super().save_user(request, user, form)
        
        # Set role based on account type
        if account_type == 'seller':
            user.role = 'SELLER'
            user.company_name = request.POST.get('company_name', '')
            user.gst_number = request.POST.get('gst_number', '')
            if commit:
                user.save()
                
                # Create seller profile if there are files
                if 'business_license' in request.FILES:
                    from .models import SellerProfile
                    SellerProfile.objects.create(
                        user=user,
                        business_license=request.FILES['business_license']
                    )
        else:
            user.role = 'BUYER'
            if commit:
                user.save()
                
                # Create buyer profile with default values
                from .models import BuyerProfile
                BuyerProfile.objects.create(
                    user=user,
                    business_type='OTHER',
                    preferred_payment_method='BANK_TRANSFER'
                )
        
        return user
