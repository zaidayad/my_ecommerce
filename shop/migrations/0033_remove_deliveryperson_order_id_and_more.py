# Generated by Django 4.0.2 on 2025-01-07 20:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0032_order_delivery_person"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="deliveryperson",
            name="order_id",
        ),
        migrations.RemoveField(
            model_name="order",
            name="delivery_person",
        ),
        migrations.AddField(
            model_name="deliveryperson",
            name="order",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="shop.order",
            ),
        ),
    ]
