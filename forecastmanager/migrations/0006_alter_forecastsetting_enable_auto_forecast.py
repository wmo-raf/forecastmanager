# Generated by Django 4.2.2 on 2023-08-07 09:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forecastmanager', '0005_alter_forecastdataparameters_parameter'),
    ]

    operations = [
        migrations.AlterField(
            model_name='forecastsetting',
            name='enable_auto_forecast',
            field=models.BooleanField(default=False, verbose_name='Enable automated forecasts'),
        ),
    ]
