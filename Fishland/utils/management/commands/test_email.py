from django.core.management.base import BaseCommand
from utils.test_email import test_email_configuration

class Command(BaseCommand):
    help = 'Test email configuration by sending a test email'

    def handle(self, *args, **kwargs):
        success, message = test_email_configuration()
        if success:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stdout.write(self.style.ERROR(message))
