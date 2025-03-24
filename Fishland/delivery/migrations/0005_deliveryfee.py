# Generated by Django 5.1.4 on 2025-02-14 05:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0004_alter_deliveryprofile_license_image_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeliveryFee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('base_fee', models.DecimalField(decimal_places=2, default=50.0, max_digits=10)),
                ('per_km_fee', models.DecimalField(decimal_places=2, default=10.0, max_digits=5)),
                ('min_distance', models.DecimalField(decimal_places=2, default=0.0, max_digits=5)),
                ('max_distance', models.DecimalField(decimal_places=2, default=20.0, max_digits=5)),
                ('free_delivery_threshold', models.DecimalField(decimal_places=2, default=1000.0, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Delivery Fee',
                'verbose_name_plural': 'Delivery Fees',
            },
        ),
    ]
