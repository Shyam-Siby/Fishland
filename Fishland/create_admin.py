import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fishland.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import User  # Import your custom user model

# Create superuser
User = get_user_model()

# Delete existing superuser if exists
User.objects.filter(email='admin@fishland.com').delete()

# Create new superuser
admin = User.objects.create_superuser(
    email='admin@fishland.com',
    username='admin',
    password='admin123',
    first_name='Admin',
    last_name='User',
    role='ADMIN'  # Make sure this matches your role choices
)

print(f"Superuser created successfully with email: {admin.email}")
