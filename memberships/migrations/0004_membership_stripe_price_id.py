# Generated by Django 3.2.25 on 2025-04-10 08:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('memberships', '0003_auto_20250408_0828'),
    ]

    operations = [
        migrations.AddField(
            model_name='membership',
            name='stripe_price_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
