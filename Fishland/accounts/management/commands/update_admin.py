from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Updates admin user role'

    def handle(self, *args, **kwargs):
        try:
            admin = User.objects.get(email="admin@fishland.com")
            admin.role = 'ADMIN'
            admin.is_superuser = True
            admin.is_staff = True
            admin.save()
            self.stdout.write(self.style.SUCCESS('Successfully updated admin user'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Admin user not found'))
