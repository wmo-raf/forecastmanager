# Generated by Django 4.2.3 on 2024-03-15 06:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('forecastmanager', '0017_forecastsetting_weather_detail_page'),
    ]

    operations = [
        migrations.DeleteModel(
            name='DailyWeather',
        ),
    ]
