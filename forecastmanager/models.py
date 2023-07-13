import uuid

from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtailgeowidget.helpers import geosgeometry_str_to_struct
from wagtailgeowidget.panels import LeafletPanel

from .blocks import ExtremeBlock
from .site_settings import ForecastPeriod


class DailyWeather(models.Model):
    issued_on = models.DateField(auto_now_add=True, null=True)
    forecast_date = models.DateField(_("Forecast Date"), auto_now=False, auto_now_add=False)
    forecast_desc = RichTextField(verbose_name=_('Weather Forecast Description'))
    summary_date = models.DateField(_("Summary Date"), auto_now=False, auto_now_add=False)
    summary_desc = RichTextField(verbose_name=_('Weather Summary Description'))
    extreme_date = models.DateField(_("Extreme Date"), auto_now=False, auto_now_add=False, null=True, blank=True)
    extremes = StreamField([
        ('extremes', ExtremeBlock())
    ], use_json_field=True)

    panels = [
        MultiFieldPanel([
            FieldPanel('summary_date'),
            FieldPanel('summary_desc'),
        ], heading="Weather Summary"),
        MultiFieldPanel([
            FieldPanel('forecast_date'),
            FieldPanel('forecast_desc'),
        ], heading="Weather Forecast"),
        MultiFieldPanel([
            FieldPanel('extreme_date'),
            FieldPanel('extremes')
        ], heading="Extremes")

    ]

    def __str__(self) -> str:
        return f'Daily Weather - Issued on {self.issued_on.strftime("%Y-%m-%d")}'


# Create your models here.
class City(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_("Unique UUID. Auto generated on creation."),
    )
    name = models.CharField(verbose_name=_("City Name"), max_length=255, null=True, blank=False, unique=True)
    location = models.PointField(verbose_name=_("City Location (Lat, Lng)"))

    panels = [
        FieldPanel("name"),
        LeafletPanel("location"),
    ]

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")

    def __str__(self) -> str:
        return self.name

    @property
    def coordinates(self):
        location = geosgeometry_str_to_struct(str(self.location))
        return [location['x'], location['y']]


class Forecast(models.Model):
    CONDITION_CHOICES = (
        ('clearsky', 'Clear sky'),
        ('cloudy', 'Cloudy'),
        ('fair', 'Fair'),
        ('fog', 'Fog'),
        ('heavyrain', 'Heavy Rain'),
        ('heavyrainandthunder', 'Heavy Rain and Thunder'),
        ('heavyrainshowers', 'Heavy Rain Showers'),
        ('heavyrainshowersandthunder', 'Heavy Rain Showers and Thunder'),
        ('heavysleet', 'Heavy Sleet'),
        ('heavysleetandthunder', 'Heavy Sleet and Thunder'),
        ('heavysleetshowers', 'Heavy Sleet Showers'),
        ('heavysleetshowersandthunder', 'Heavy Sleet Showers and Thunder'),
        ('heavysnow', 'Heavy Snow'),
        ('heavysnowandthunder', 'Heavy Snow and Thunder'),
        ('heavysnowshowers', 'Heavy Snow Showers'),
        ('heavysnowshowersandthunder', 'Heavy Snow Showers and Thunder'),
        ('lightrain', 'Light Rain'),
        ('lightrainandthunder', 'Light Rain and Thunder'),
        ('lightrainshowers', 'Light Rain Showers'),
        ('lightrainshowersandthunder', 'Light Rain Showers and Thunder'),
        ('lightsleet', 'Light Sleet'),
        ('lightsleetandthunder', 'Light Sleet and Thunder'),
        ('lightsleetshowers', 'Light Sleet Showers'),
        ('lightsleetshowersandthunder', 'Light Sleet Showers and Thunder'),
        ('lightsnowshowersandthunder', 'Light Snow Showers and Thunder'),
        ('partlycloudy', 'Partly Cloudy'),
        ('rain', 'Rain'),
        ('rainandthunder', 'Rain and Thunder'),
        ('rainshowers', 'Rain showers'),
        ('rainshowersandthunder', 'Rain Showes and Thunder'),
        ('sleet', 'Sleet'),
        ('sleetandthunder', 'Sleet and Thunder'),
        ('sleetshowers', 'Sleet Showers'),
        ('sleetshowersandthunder', 'Sleet Showes and Thunder'),
        ('snow', 'Snow'),
        ('snowandthunder', 'Snow and Thunder'),
        ('snowshowers', 'Snow Showers'),
        ('snowshowersandthunder', 'Snow Showers and Thunder'),

    )

    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name=_("City"))
    forecast_date = models.DateField(auto_now=False, auto_now_add=False, verbose_name=_("Forecasts Date"))
    effective_period = models.ForeignKey(ForecastPeriod, on_delete=models.PROTECT, null=True)
    condition = models.CharField(choices=CONDITION_CHOICES, verbose_name=_("General Weather Condition"),
                                 help_text=_("E.g Light Showers"), null=True, max_length=255)
    data_value = models.JSONField(null=True)

    class Meta:
        unique_together = ("city", "forecast_date", "effective_period")
        verbose_name = _("Forecast")
        verbose_name_plural = _("Forecasts")
