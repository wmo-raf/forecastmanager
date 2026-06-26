from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forecastmanager', '0032_alter_forecastsetting_auto_publish_forecasts'),
    ]

    operations = [
        migrations.AddField(
            model_name='forecastsetting',
            name='geonames_username',
            field=models.CharField(
                blank=True,
                null=True,
                max_length=100,
                help_text='Username for the free GeoNames web service (https://www.geonames.org/login), used to import cities. Web services must be enabled for the account.',
                verbose_name='GeoNames username',
            ),
        ),
    ]
