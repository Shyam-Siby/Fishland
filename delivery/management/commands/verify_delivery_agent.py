from django.core.management.base import BaseCommand
from delivery.models import DeliveryProfile

class Command(BaseCommand):
    help = 'Verify delivery agents and update their status'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email of the delivery agent to verify')
        parser.add_argument('--status', type=str, choices=['ONLINE', 'OFFLINE'], default='ONLINE',
                          help='Status to set for the delivery agent')

    def handle(self, *args, **options):
        email = options['email']
        status = options['status']
        
        try:
            delivery_profile = DeliveryProfile.objects.get(user__email=email)
            delivery_profile.is_verified = True
            delivery_profile.status = status
            delivery_profile.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully verified delivery agent {delivery_profile.user.get_full_name()} '
                    f'and set status to {status}'
                )
            )
        except DeliveryProfile.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f'No delivery agent found with email {email}'
                )
            ) 