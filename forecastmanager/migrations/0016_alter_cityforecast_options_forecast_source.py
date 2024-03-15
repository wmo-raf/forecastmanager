# Generated by Django 4.2.3 on 2024-03-08 12:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forecastmanager', '0015_alter_forecast_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cityforecast',
            options={'ordering': ['parent__forecast_date', 'parent__effective_period']},
        ),
        migrations.AddField(
            model_name='forecast',
            name='source',
            field=models.CharField(choices=[('local', 'NMHSs Forecast'), ('yr', 'yr.no')], default='local', max_length=100),
        ),
    ]