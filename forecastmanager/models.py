import uuid

from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, InlinePanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Orderable
from wagtailgeowidget import geocoders
from wagtailgeowidget.helpers import geosgeometry_str_to_struct
from wagtailgeowidget.panels import LeafletPanel, GeoAddressPanel

from .blocks import ExtremeBlock
from .forms import ForecastForm
from .site_settings import ForecastPeriod, WeatherCondition, ForecastDataParameters


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
        GeoAddressPanel("name", geocoder=geocoders.NOMINATIM),
        LeafletPanel("location", address_field="name"),
    ]

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def coordinates(self):
        location = geosgeometry_str_to_struct(str(self.location))
        return [location['x'], location['y']]


class Forecast(ClusterableModel):
    base_form_class = ForecastForm

    forecast_date = models.DateField(auto_now=False, auto_now_add=False, verbose_name=_("Forecasts Date"))
    effective_period = models.ForeignKey(ForecastPeriod, on_delete=models.PROTECT, null=True)

    class Meta:
        unique_together = ("forecast_date", "effective_period")
        verbose_name = _("Forecast")
        verbose_name_plural = _("Forecasts")

    panels = [
        FieldPanel("forecast_date"),
        FieldPanel("effective_period"),
        # InlinePanel("city_forecasts", label=_("City Forecast Data")),
    ]

    def __str__(self):
        return f"{self.forecast_date} - {self.effective_period.label}"


class CityForecast(ClusterableModel, Orderable):
    parent = ParentalKey(Forecast, on_delete=models.CASCADE, related_name="city_forecasts")
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name=_("City"))
    condition = models.ForeignKey(WeatherCondition, blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("parent", "city")

    panels = [
        FieldPanel("city"),
        FieldPanel("condition"),
        InlinePanel("data_values", label=_("Forecast Data Values")),
    ]

    def __str__(self):
        return f"{self.city.name}"


class DataValue(ClusterableModel, Orderable):
    parent = ParentalKey(CityForecast, on_delete=models.CASCADE, related_name="data_values")
    parameter = models.ForeignKey(ForecastDataParameters, on_delete=models.CASCADE, related_name="data_values")
    value = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Value"))

    class Meta:
        unique_together = ("parent", "parameter")


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
