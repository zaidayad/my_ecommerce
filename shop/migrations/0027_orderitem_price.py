# Generated by Django 4.0.2 on 2025-01-04 10:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0026_remove_product_quantity_remaining_alter_order_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="price",
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
    ]
