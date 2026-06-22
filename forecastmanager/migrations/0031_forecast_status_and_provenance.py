from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forecastmanager', '0030_forecast_provider_and_parameter_mapping'),
    ]

    operations = [
        migrations.AddField(
            model_name='forecastsetting',
            name='auto_publish_forecasts',
            field=models.BooleanField(
                default=True,
                help_text=(
                    'When off, automated forecasts are saved as drafts for a forecaster '
                    'to review and publish. When on, they are published immediately.'
                ),
                verbose_name='Auto-publish automated forecasts',
            ),
        ),
        migrations.AddField(
            model_name='forecast',
            name='status',
            field=models.CharField(
                choices=[('draft', 'Draft'), ('published', 'Published')],
                default='published',
                help_text='Only published forecasts are served on the public API/website.',
                max_length=20,
                verbose_name='Status',
            ),
        ),
        migrations.AlterField(
            model_name='forecast',
            name='source',
            field=models.CharField(
                choices=[('local', 'NMHSs Forecast'), ('yr', 'yr.no'), ('open_meteo', 'Open-Meteo')],
                default='local',
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name='cityforecast',
            name='data_source',
            field=models.CharField(
                choices=[('auto', 'Automated'), ('manual', 'Manual / Forecaster')],
                default='manual',
                help_text=(
                    "Whether this city's values were entered by a forecaster or generated "
                    'automatically. Automated runs never overwrite forecaster-authored data.'
                ),
                max_length=20,
                verbose_name='Data source',
            ),
        ),
    ]
