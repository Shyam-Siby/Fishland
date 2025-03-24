from django.core.management.base import BaseCommand
from accounts.models import User, BuyerProfile

class Command(BaseCommand):
    help = 'Create buyer profiles for users who do not have one'

    def handle(self, *args, **kwargs):
        users = User.objects.filter(role=User.Role.BUYER)
        created_count = 0
        
        for user in users:
            try:
                user.buyer_profile
            except BuyerProfile.DoesNotExist:
                BuyerProfile.objects.create(user=user)
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} buyer profiles'
            )
        )
