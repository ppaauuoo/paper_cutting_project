# Generated by Django 4.2.13 on 2024-08-24 09:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('order_optimization', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='planorder',
            old_name='production_quantity',
            new_name='plan_quantity',
        ),
    ]
