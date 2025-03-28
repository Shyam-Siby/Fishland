# Generated by Django 5.0 on 2025-01-15 06:44

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0005_alter_address_options_address_label_and_more'),
        ('seller', '0002_remove_deliveryboy_email_remove_deliveryboy_name_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderDelivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('picked_up', 'Picked Up'), ('in_transit', 'In Transit'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('delivery_boy', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deliveries', to='seller.deliveryboy')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='delivery', to='orders.order')),
            ],
            options={
                'verbose_name': 'Order Delivery',
                'verbose_name_plural': 'Order Deliveries',
                'ordering': ['-created_at'],
            },
        ),
    ]
