from django.db import migrations, models
import django.db.models.deletion
import modelcluster.fields


PROVIDER_CHOICES = [
    ('yr', 'yr.no (Met Norway)'),
    ('open_meteo', 'Open-Meteo'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('forecastmanager', '0029_forecastsetting_use_period_labels'),
    ]

    operations = [
        migrations.AddField(
            model_name='forecastsetting',
            name='forecast_provider',
            field=models.CharField(
                choices=PROVIDER_CHOICES,
                default='yr',
                help_text='Which weather API to fetch automated forecasts from.',
                max_length=50,
                verbose_name='Automated forecast provider',
            ),
        ),
        migrations.CreateModel(
            name='ForecastProviderParameterMapping',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sort_order', models.IntegerField(blank=True, editable=False, null=True)),
                ('provider', models.CharField(choices=PROVIDER_CHOICES, max_length=50, verbose_name='Provider')),
                ('source_field', models.CharField(max_length=100, verbose_name='Provider source field')),
                ('parameter', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='provider_mappings',
                    to='forecastmanager.forecastdataparameters',
                    verbose_name='Database parameter',
                )),
                ('parent', modelcluster.fields.ParentalKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='provider_parameter_mappings',
                    to='forecastmanager.forecastsetting',
                )),
            ],
            options={
                'ordering': ['sort_order'],
                'abstract': False,
            },
        ),
        migrations.AlterUniqueTogether(
            name='forecastproviderparametermapping',
            unique_together={('parent', 'provider', 'source_field')},
        ),
    ]
