# Generated by Django 5.1.4 on 2025-03-05 14:53

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0011_order_cancellation_note_order_cancellation_reason_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderitem',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_items', to='orders.order'),
        ),
    ]
