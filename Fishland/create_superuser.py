import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fishland.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@fishland.com', 'admin123')
    print("Superuser created successfully!")
else:
    print("Superuser already exists!")
