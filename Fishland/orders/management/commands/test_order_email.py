from django.core.management.base import BaseCommand
from orders.models import Order
from orders.utils import send_order_confirmation_email

class Command(BaseCommand):
    help = 'Test order confirmation email by sending it for a specific order'

    def add_arguments(self, parser):
        parser.add_argument('order_number', type=str, help='The order number to send email for')

    def handle(self, *args, **options):
        try:
            order = Order.objects.get(order_number=options['order_number'])
            send_order_confirmation_email(order)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully sent test email for order {order.order_number}')
            )
        except Order.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Order {options["order_number"]} not found')
            )
