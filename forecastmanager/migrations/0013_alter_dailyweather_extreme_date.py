# Generated by Django 4.2.2 on 2023-07-04 12:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forecastmanager', '0012_dailyweather_extreme_date_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dailyweather',
            name='extreme_date',
            field=models.DateField(blank=True, null=True, verbose_name='Extreme Date'),
        ),
    ]
