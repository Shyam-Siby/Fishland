from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a superuser with email as identifier'

    def handle(self, *args, **options):
        if not User.objects.filter(email='admin@fishland.com').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@fishland.com',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )
            self.stdout.write(self.style.SUCCESS('Superuser created successfully'))
