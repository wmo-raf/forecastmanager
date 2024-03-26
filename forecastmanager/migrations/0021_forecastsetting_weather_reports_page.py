# Generated by Django 4.2.3 on 2024-03-26 10:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0089_log_entry_data_json_null_to_object'),
        ('forecastmanager', '0020_alter_city_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='forecastsetting',
            name='weather_reports_page',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='weather_reports_page', to='wagtailcore.page'),
        ),
    ]