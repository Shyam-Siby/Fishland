from django.core.management.base import BaseCommand
from delivery.models import DeliveryFee

class Command(BaseCommand):
    help = 'Set up initial delivery fee configuration'

    def handle(self, *args, **kwargs):
        # Deactivate any existing delivery fees
        DeliveryFee.objects.update(is_active=False)
        
        # Create new active delivery fee
        delivery_fee = DeliveryFee.objects.create(
            base_fee=50.00,  # Base delivery fee
            per_km_fee=10.00,  # Fee per kilometer
            min_distance=1.00,  # Minimum distance in km
            max_distance=20.00,  # Maximum distance in km
            free_delivery_threshold=10000.00,  # Free delivery for orders above this amount
            is_active=True
        )
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created delivery fee configuration: {delivery_fee}'))
