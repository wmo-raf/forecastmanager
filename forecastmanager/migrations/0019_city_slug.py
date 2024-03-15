# Generated by Django 4.2.3 on 2024-03-15 07:48

import django_extensions.db.fields
from django.db import migrations

from forecastmanager.models import City


def migrate_data_forward(apps, schema_editor):
    for instance in City.objects.all():
        print(f"Generating slug for {instance}")
        instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('forecastmanager', '0018_delete_dailyweather'),
    ]

    operations = [
        migrations.AddField(
            model_name='city',
            name='slug',
            field=django_extensions.db.fields.AutoSlugField(blank=True, default=None, editable=False, null=True,
                                                            populate_from='name', unique=True),
            preserve_default=False
        ),
        migrations.RunPython(
            migrate_data_forward,
            migrations.RunPython.noop
        ),

    ]
