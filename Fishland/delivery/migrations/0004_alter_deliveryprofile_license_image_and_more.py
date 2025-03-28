# Generated by Django 5.0 on 2025-02-11 06:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0003_deliveryprofile_is_active_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deliveryprofile',
            name='license_image',
            field=models.ImageField(blank=True, null=True, upload_to='delivery_documents/licenses/'),
        ),
        migrations.AlterField(
            model_name='deliveryprofile',
            name='status',
            field=models.CharField(choices=[('ONLINE', 'Online'), ('OFFLINE', 'Offline'), ('BUSY', 'Busy'), ('ON_DELIVERY', 'On Delivery')], default='OFFLINE', max_length=15),
        ),
    ]
