# Generated by Django 5.1.4 on 2025-02-13 05:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0010_order_delivery_assigned_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='cancellation_note',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='cancellation_reason',
            field=models.CharField(blank=True, choices=[('OUT_OF_STOCK', 'Out of Stock'), ('PRICE_MISMATCH', 'Price Mismatch'), ('QUALITY_ISSUES', 'Quality Issues'), ('DELIVERY_ISSUES', 'Cannot Deliver to Location'), ('OTHER', 'Other')], max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='payment_method',
            field=models.CharField(choices=[('COD', 'Cash on Delivery'), ('ONLINE', 'Online Payment')], default='COD', max_length=20),
        ),
    ]
