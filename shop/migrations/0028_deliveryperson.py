# Generated by Django 4.0.2 on 2025-01-06 19:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0027_orderitem_price"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeliveryPerson",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("phone_number", models.CharField(max_length=15)),
                ("age", models.IntegerField()),
                ("date_added", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
