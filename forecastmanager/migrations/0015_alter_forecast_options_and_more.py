# Generated by Django 4.2.3 on 2024-03-08 09:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forecastmanager', '0014_alter_forecastsetting_default_city'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='forecast',
            options={'ordering': ['forecast_date', 'effective_period'], 'verbose_name': 'Forecast', 'verbose_name_plural': 'Forecasts'},
        ),
        migrations.AlterUniqueTogether(
            name='forecastperiod',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='forecastperiod',
            name='default',
            field=models.BooleanField(default=False, verbose_name='Is default'),
        ),
        migrations.AlterUniqueTogether(
            name='forecastperiod',
            unique_together={('default', 'forecast_effective_time')},
        ),
        migrations.RemoveField(
            model_name='forecastperiod',
            name='whole_day',
        ),
    ]
