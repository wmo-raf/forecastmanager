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


@register_setting
class ForecastSetting(ClusterableModel, BaseSiteSetting):
    enable_auto_forecast = models.BooleanField(
        default=True,
        verbose_name=_('Enable automated forecasts')
    )

    TEMPERATURE_UNITS = (
        ("celsius", "°C"),
        ("fareinheit", "°F"),
        ("kelvin", "K")
    )
    WIND_UNITS = (
        ("knots", "knots"),
        ("km_p_hr", "km/h"),
        ("mtr_p_s", "m/s"),
        ("mile_p_hr", "mph"),
        ("feet_p_s", "ft/s")
    )
    temp_units = models.CharField(choices=TEMPERATURE_UNITS, default='celsius', max_length=255,
                                  verbose_name=_("Temperature"))
    wind_units = models.CharField(choices=WIND_UNITS, default='km_p_hr', max_length=255, verbose_name=_("Wind"))

    edit_handler = TabbedInterface([
        ObjectList([
            InlinePanel('data_parameters', heading=_("Data Parameters"), label=_("Data Parameter")),
        ], heading=_("Forecast Data Parameters")),
        ObjectList([
            InlinePanel('periods', heading=_("Forecast Periods"), label=_("Forecast Period")),
        ], heading=_("Forecast Periods")),
        ObjectList([
            FieldPanel('enable_auto_forecast'),
        ], heading=_("Forecast Source")),
        ObjectList([
            FieldPanel("temp_units"),
            FieldPanel("wind_units"),
        ], heading=_("Measurement Units")),
    ])

    @cached_property
    def data_parameter_values(self):
        data_parameters = self.data_parameters.all()
        params = []
        for param in data_parameters:
            params.append({"parameter": param.parameter, "name": param.name, "parameter_type": param.parameter_type})
        return params


class ForecastPeriod(Orderable):
    parent = ParentalKey(ForecastSetting, on_delete=models.CASCADE, related_name="periods")
    forecast_effective_time = models.TimeField(unique=True, verbose_name=_("Forecast Effective Time"))
    label = models.CharField(max_length=100, verbose_name=_("Label"))
    whole_day = models.BooleanField(default=False, verbose_name=_("Is Whole Day"))


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

    PARAMETER_TYPE_CHOICES =(
        ("text", _("Text")),
        ("numeric", _("Number")),
        ("time", _("Time")),
    )

    parent = ParentalKey(ForecastSetting, on_delete=models.CASCADE, related_name="data_parameters")
    parameter = models.CharField(max_length=100, choices=PARAMETER_CHOICES, unique=True, verbose_name=_("Parameter"))
    name = models.CharField(max_length=100, verbose_name=_("Parameter Label"),
                            help_text=_("Parameter name as locally labelled"))
    parameter_type = models.CharField(max_length=100, choices=PARAMETER_TYPE_CHOICES, verbose_name=_("Parameter Type"), default="text")


    def __str__(self):
        return self.name
