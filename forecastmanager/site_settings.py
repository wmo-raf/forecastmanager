from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import (
    FieldPanel,
    TabbedInterface,
    ObjectList, InlinePanel,
)
from wagtail.contrib.settings.models import BaseSiteSetting
from wagtail.contrib.settings.registry import register_setting
from wagtail.models import Orderable

from forecastmanager.widgets import WeatherSymbolChooserWidget


@register_setting
class ForecastSetting(ClusterableModel, BaseSiteSetting):
    enable_auto_forecast = models.BooleanField(
        default=False,
        verbose_name=_('Enable automated forecasts')
    )

    default_city = models.ForeignKey("City", on_delete=models.CASCADE, verbose_name=_("Default City"), null=True,
                                     blank=True, help_text="City will appear as first in homepage city forecasts")

    edit_handler = TabbedInterface([
        ObjectList([
            InlinePanel('periods', heading=_("Forecast Periods"), label=_("Forecast Period")),
        ], heading=_("Forecast Periods")),
        ObjectList([
            InlinePanel('data_parameters', heading=_("Data Parameters"), label=_("Data Parameter")),
        ], heading=_("Forecast Data Parameters")),
        ObjectList([
            InlinePanel('weather_conditions', heading=_("Weather Conditions"), label=_("Weather Condition")),
        ], heading=_("Forecast Weather Conditions")),
        ObjectList([
            FieldPanel('enable_auto_forecast'),
        ], heading=_("Forecast Source")),
        ObjectList([
            FieldPanel('default_city'),
        ], heading=_("Default City")),
    ])

    @cached_property
    def data_parameter_values(self):
        data_parameters = self.data_parameters.all()
        params = []
        for param in data_parameters:
            params.append({"parameter": param.parameter, "name": param.name, "parameter_type": param.parameter_type,
                           "parameter_unit": param.parameter_unit if param.parameter_unit else " "})
        return params

    @property
    def periods_as_choices(self):
        return [(period.id, period.label) for period in self.periods.all()]

    @property
    def weather_conditions_list(self):
        weather_conditions = self.weather_conditions.all()
        return [c.alias if c.alias else c.label for c in weather_conditions]


class ForecastPeriod(Orderable):
    parent = ParentalKey(ForecastSetting, on_delete=models.CASCADE, related_name="periods")
    whole_day = models.BooleanField(default=False, verbose_name=_("Is Whole Day"))
    forecast_effective_time = models.TimeField(verbose_name=_("Forecast Effective Time"))
    label = models.CharField(max_length=100, verbose_name=_("Label"))

    class Meta:
        unique_together = ("whole_day", "forecast_effective_time")

    def __str__(self):
        return self.label


class ForecastDataParameters(Orderable):
    PARAMETER_CHOICES = (
        ("air_temperature_max", _("Maximum Air Temperature")),
        ("air_temperature_min", _("Minimum Air Temperature")),
        ("air_temperature", _("Air Temperature")),
        ("dew_point_temperature", _("Dew Point Temperature")),
        ("precipitation_amount", _("Precipitation Amount")),
        ("air_pressure_at_sea_level", _("Air Pressure (Sea level)")),
        ("wind_speed", _("Wind Speed")),
        ("wind_from_direction", _("Wind Direction")),
        ("relative_humidity", _("Relative Humidity")),
        ("sunrise", _("Sunrise")),
        ("sunset", _("Sunset")),
        ("moonrise", _("Moonrise")),
        ("moonset", _("Moonset")),
    )

    PARAMETER_TYPE_CHOICES = (
        ("numeric", _("Number")),
        ("time", _("Time")),
        ("text", _("Text")),
    )

    parent = ParentalKey(ForecastSetting, on_delete=models.CASCADE, related_name="data_parameters")
    parameter = models.CharField(max_length=100, choices=PARAMETER_CHOICES, unique=True, verbose_name=_("Parameter"))
    name = models.CharField(max_length=100, verbose_name=_("Parameter Label"),
                            help_text=_("Parameter name as locally labelled"))
    parameter_type = models.CharField(max_length=100, choices=PARAMETER_TYPE_CHOICES, verbose_name=_("Parameter Type"),
                                      default="numeric")
    parameter_unit = models.CharField(_("Unit of measurement"), max_length=100, null=True, blank=True,
                                      help_text="e.g °C, %, mm, hPa, etc ")

    def __str__(self):
        return self.name


class WeatherCondition(Orderable):
    parent = ParentalKey(ForecastSetting, on_delete=models.CASCADE, related_name="weather_conditions")
    symbol = models.CharField(max_length=100, verbose_name=_("Weather Symbol"))
    label = models.CharField(max_length=100, unique=True, verbose_name=_("Label"))
    alias = models.CharField(max_length=100, blank=True, null=True, unique=True, verbose_name=_("Alias"))

    panels = [
        FieldPanel('symbol', widget=WeatherSymbolChooserWidget),
        FieldPanel('label'),
        FieldPanel('alias'),
    ]

    def __str__(self):
        return self.label
