# Generated by Django 5.0 on 2025-01-10 08:51

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StockAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('threshold_quantity', models.DecimalField(decimal_places=2, max_digits=10)),
                ('is_active', models.BooleanField(default=True)),
                ('last_notification_sent', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='stock_alert', to='products.product')),
            ],
        ),
        migrations.CreateModel(
            name='StockHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('previous_quantity', models.DecimalField(decimal_places=2, max_digits=10)),
                ('new_quantity', models.DecimalField(decimal_places=2, max_digits=10)),
                ('change_type', models.CharField(choices=[('ADDITION', 'Stock Added'), ('REDUCTION', 'Stock Reduced'), ('ADJUSTMENT', 'Stock Adjusted'), ('SALE', 'Stock Sold')], max_length=20)),
                ('change_reason', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('changed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stock_history', to='products.product')),
            ],
            options={
                'verbose_name_plural': 'Stock Histories',
                'ordering': ['-created_at'],
            },
        ),
    ]
