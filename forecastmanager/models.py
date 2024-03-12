import uuid

from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, InlinePanel
from wagtail.api.v2.utils import get_full_url
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Orderable
from wagtailgeowidget import geocoders
from wagtailgeowidget.helpers import geosgeometry_str_to_struct
from wagtailgeowidget.panels import LeafletPanel, GeoAddressPanel

from .blocks import ExtremeBlock
from .forecast_settings import (
    ForecastPeriod,
    WeatherCondition,
    ForecastDataParameters
)
from .forms import ForecastForm


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
    def clean_name(self):
        return self.name.replace(" ", "--")

    @property
    def coordinates(self):
        location = geosgeometry_str_to_struct(str(self.location))
        return [float(location['x']), float(location['y'])]

    @property
    def x(self):
        return self.coordinates[0]

    @property
    def y(self):
        return self.coordinates[1]


class Forecast(ClusterableModel):
    base_form_class = ForecastForm

    FORECAST_SOURCE_CHOICES = [
        ("local", _("NMHSs Forecast")),
        ("yr", _("yr.no")),
    ]

    forecast_date = models.DateField(auto_now=False, auto_now_add=False, verbose_name=_("Forecasts Date"))
    effective_period = models.ForeignKey(ForecastPeriod, on_delete=models.PROTECT, null=True)
    source = models.CharField(max_length=100, choices=FORECAST_SOURCE_CHOICES, default="local")

    class Meta:
        unique_together = ("forecast_date", "effective_period")
        verbose_name = _("Forecast")
        verbose_name_plural = _("Forecasts")
        ordering = ["forecast_date", "effective_period"]

    panels = [
        FieldPanel("forecast_date"),
        FieldPanel("effective_period"),
        FieldPanel("replace_existing"),
        # InlinePanel("city_forecasts", label=_("City Forecast Data")),
    ]

    def __str__(self):
        return f"{self.forecast_date} - {self.effective_period.label}"

    def get_geojson(self, request=None):
        features = []
        for city_forecast in self.city_forecasts.all():
            features.append(city_forecast.get_geojson_feature(request))
        return {
            "type": "FeatureCollection",
            "features": features,
        }


class CityForecast(ClusterableModel, Orderable):
    parent = ParentalKey(Forecast, on_delete=models.CASCADE, related_name="city_forecasts")
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name=_("City"))
    condition = models.ForeignKey(WeatherCondition, blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("parent", "city")
        ordering = ["parent__forecast_date", "parent__effective_period"]

    panels = [
        FieldPanel("city"),
        FieldPanel("condition"),
        InlinePanel("data_values", label=_("Forecast Data Values")),
    ]

    def __str__(self):
        return f"{self.city.name} - {self.parent.forecast_date} - {self.parent.effective_period.label}"

    @property
    def forecast_date(self):
        return self.parent.forecast_date

    @property
    def effective_period(self):
        return self.parent.effective_period

    @property
    def data_values_dict(self):
        data_values = {}
        for data_value in self.data_values.all():
            data_values[data_value.parameter.parameter] = {
                "value": data_value.parsed_value,
                "label": data_value.parameter.parameter_info.get("label"),
                "units": data_value.parameter.parameter_info.get("unit"),
                "value_with_units": data_value.value_with_units,
            }

        # Group temperature values
        temperature = {}
        if "air_temperature_max" in data_values:
            temperature["max_temp"] = data_values.get("air_temperature_max")
        if "air_temperature_min" in data_values:
            temperature["min_temp"] = data_values.get("air_temperature_min")
        if "air_temperature" in data_values:
            temperature["temp"] = data_values.get("air_temperature")
        if temperature:
            data_values["temperature"] = temperature

        return data_values

    def get_geojson_feature(self, request=None):
        condition_symbol_url = get_full_url(request, self.condition.icon_url)

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": self.city.coordinates,
            },
            "properties": {
                "date": self.parent.forecast_date,
                "effective_period_time": self.parent.effective_period.forecast_effective_time,
                "effective_period_label": self.parent.effective_period.label,
                "city": self.city.name,
                "condition": self.condition.symbol,
                "condition_label": self.condition.label,
                "condition_symbol_url": condition_symbol_url
            },
        }

        parameter_values = {}
        for data_value in self.data_values.all():
            parameter_values[data_value.parameter.parameter] = data_value.parsed_value

        feature["properties"].update(parameter_values)

        return feature


class DataValue(ClusterableModel, Orderable):
    parent = ParentalKey(CityForecast, on_delete=models.CASCADE, related_name="data_values")
    parameter = models.ForeignKey(ForecastDataParameters, on_delete=models.CASCADE, related_name="data_values")
    value = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Value"))

    class Meta:
        unique_together = ("parent", "parameter")

    @property
    def parsed_value(self):
        return self.parameter.parse_value(self.value)

    @property
    def value_with_units(self):
        return f"{self.parsed_value}{self.parameter.parameter_info.get('unit')}"


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

    def __str__(self):
        return f'Daily Weather - Issued on {self.issued_on.strftime("%Y-%m-%d")}'
