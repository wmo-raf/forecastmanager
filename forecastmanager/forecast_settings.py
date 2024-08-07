from django.db import models
from django.templatetags.static import static
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

from forecastmanager.constants import WEATHER_PARAMETERS_AS_DICT
from forecastmanager.widgets import WeatherSymbolChooserWidget, DataParameterWidget


@register_setting
class ForecastSetting(ClusterableModel, BaseSiteSetting):
    enable_auto_forecast = models.BooleanField(default=False, verbose_name=_('Enable automated forecasts'))
    default_city = models.ForeignKey("City", blank=True, null=True, on_delete=models.SET_NULL,
                                     verbose_name=_("Default City"))
    weather_detail_page = models.ForeignKey("wagtailcore.Page", blank=True, null=True, on_delete=models.SET_NULL, )
    weather_reports_page = models.ForeignKey("wagtailcore.Page", blank=True, null=True, on_delete=models.SET_NULL,
                                             related_name="weather_reports_page")
    show_conditions_label_on_widget = models.BooleanField(default=True,
                                                          verbose_name=_("Show conditions label on widget"))

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
            FieldPanel('weather_detail_page'),
            FieldPanel('weather_reports_page'),
            FieldPanel('show_conditions_label_on_widget'),
        ], heading=_("Other Settings")),
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
    def effective_periods(self):
        return [
            {"label": period.label, "time": period.forecast_effective_time}
            for period in self.periods.all()]

    @property
    def weather_conditions_list(self):
        weather_conditions = self.weather_conditions.all()
        return [c.alias if c.alias else c.label for c in weather_conditions]


class ForecastPeriod(Orderable):
    parent = ParentalKey(ForecastSetting, on_delete=models.CASCADE, related_name="periods")
    forecast_effective_time = models.TimeField(verbose_name=_("Forecast Effective Time"), unique=True)
    label = models.CharField(max_length=100, verbose_name=_("Label"))

    class Meta:
        ordering = ["forecast_effective_time"]

    panels = [
        FieldPanel('forecast_effective_time'),
        FieldPanel('label'),
    ]

    def __str__(self):
        return self.label


class ForecastDataParameters(Orderable):
    PARAMETER_TYPE_CHOICES = (
        ("numeric", _("Number")),
        ("text", _("Text")),
    )
    parent = ParentalKey(ForecastSetting, on_delete=models.CASCADE, related_name="data_parameters")
    use_known_parameters = models.BooleanField(default=True, verbose_name=_("Use predefined parameters"))
    parameter = models.CharField(max_length=100, unique=True, verbose_name=_("Parameter"))
    name = models.CharField(max_length=100, verbose_name=_("Parameter Label"),
                            help_text=_("Parameter name as locally labelled"))
    parameter_type = models.CharField(max_length=100, choices=PARAMETER_TYPE_CHOICES, verbose_name=_("Parameter Type"),
                                      default="numeric")
    parameter_unit = models.CharField(_("Unit of measurement"), max_length=100, null=True, blank=True,
                                      help_text="e.g °C, %, mm, hPa, etc ")
    show_on_home_widget = models.BooleanField(default=True, verbose_name=_("Show on Home Widget"))

    panels = [
        FieldPanel('use_known_parameters'),
        FieldPanel('parameter', widget=DataParameterWidget),
        FieldPanel('name'),
        FieldPanel('parameter_type'),
        FieldPanel('parameter_unit'),
        FieldPanel('show_on_home_widget'),
    ]

    def __str__(self):
        return self.name

    @property
    def units(self):
        if self.parameter_unit:
            return self.parameter_unit

        if self.parameter_info:
            return self.parameter_info.get("units")

        return None

    @property
    def parameter_info(self):
        return WEATHER_PARAMETERS_AS_DICT.get(self.parameter)

    def parse_value(self, value):
        if self.parameter_type == "numeric":
            return float(value)
        return value


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

    @property
    def icon_url(self):
        return static('forecastmanager/weathericons/{}.png'.format(self.symbol))
