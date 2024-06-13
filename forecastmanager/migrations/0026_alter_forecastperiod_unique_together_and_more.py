# Generated by Django 4.2.3 on 2024-06-13 09:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forecastmanager', '0025_alter_forecast_options_alter_forecastperiod_options'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='forecastperiod',
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name='forecastperiod',
            name='forecast_effective_time',
            field=models.TimeField(unique=True, verbose_name='Forecast Effective Time'),
        ),
        migrations.RemoveField(
            model_name='forecastperiod',
            name='default',
        ),
    ]