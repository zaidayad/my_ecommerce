# Generated by Django 4.0.2 on 2025-01-07 19:46

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0031_deliveryperson_order_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="delivery_person",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="shop.deliveryperson",
            ),
        ),
    ]
