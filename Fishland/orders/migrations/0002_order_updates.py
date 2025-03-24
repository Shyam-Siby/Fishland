from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='order',
            old_name='address',
            new_name='delivery_address',
        ),
        migrations.RenameField(
            model_name='order',
            old_name='total_amount',
            new_name='total',
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_date',
            field=models.DateField(default='2025-01-09'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_time',
            field=models.CharField(default='10:00', max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_fee',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='subtotal',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='order_items', to='products.product'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='quantity',
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
        migrations.RenameField(
            model_name='orderitem',
            old_name='product_price',
            new_name='price_per_kg',
        ),
        migrations.AddField(
            model_name='orderitem',
            name='total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
    ]
