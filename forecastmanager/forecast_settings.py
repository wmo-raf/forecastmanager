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
from forecastmanager.providers import PROVIDER_YR, get_provider_choices
from forecastmanager.widgets import (
    WeatherSymbolChooserWidget,
    DataParameterWidget,
    ProviderFieldWidget,
)


@register_setting
class ForecastSetting(ClusterableModel, BaseSiteSetting):
    enable_auto_forecast = models.BooleanField(default=False, verbose_name=_('Enable automated forecasts'))
    forecast_provider = models.CharField(
        max_length=50,
        choices=get_provider_choices(),
        default=PROVIDER_YR,
        verbose_name=_("Automated forecast provider"),
        help_text=_("Which weather API to fetch automated forecasts from."),
    )
    auto_publish_forecasts = models.BooleanField(
        default=True,
        verbose_name=_("Auto-publish automated forecasts"),
        help_text=_(
            "When off, automated forecasts are saved as drafts for a forecaster to "
            "review and publish. When on, they are published immediately."
        ),
    )
    default_city = models.ForeignKey("City", blank=True, null=True, on_delete=models.SET_NULL,
                                     verbose_name=_("Default City"))
    weather_detail_page = models.ForeignKey("wagtailcore.Page", blank=True, null=True, on_delete=models.SET_NULL, )
    weather_reports_page = models.ForeignKey("wagtailcore.Page", blank=True, null=True, on_delete=models.SET_NULL,
                                             related_name="weather_reports_page")
    show_conditions_label_on_widget = models.BooleanField(default=True,
                                                          verbose_name=_("Show conditions label on widget"))
    
    use_period_labels = models.BooleanField(default=False,
                                            verbose_name=_("Use Period Labels inplace of forecast time"), )
    
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
            FieldPanel('forecast_provider'),
            FieldPanel('auto_publish_forecasts'),
            InlinePanel(
                'provider_parameter_mappings',
                heading=_("Provider Parameter Mapping"),
                label=_("Parameter Mapping"),
                help_text=_(
                    "Map a source field from the selected provider to one of your "
                    "forecast data parameters. Add a row for each parameter you want "
                    "the automated forecast to populate."
                ),
            ),
        ], heading=_("Forecast Source")),
        ObjectList([
            FieldPanel('default_city'),
            FieldPanel('weather_detail_page'),
            FieldPanel('weather_reports_page'),
            FieldPanel('use_period_labels'),
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

    def get_provider_field_map(self, provider=None):
        """
        Return the admin-configured field map for a provider.

        Args:
            provider: Provider key (e.g. "open_meteo"). Defaults to the
                currently selected ``forecast_provider``.

        Returns:
            Dict mapping a provider source field to a ForecastDataParameter key,
            e.g. ``{"temperature_2m": "air_temperature"}``. Empty when nothing
            has been mapped, in which case callers should fall back to their
            built-in defaults.
        """
        provider = provider or self.forecast_provider
        field_map = {}
        for mapping in self.provider_parameter_mappings.filter(provider=provider):
            if mapping.source_field and mapping.parameter_id:
                field_map[mapping.source_field] = mapping.parameter.parameter
        return field_map


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
        return static('forecastmanager/weathericons/{}.svg'.format(self.symbol))


class ForecastProviderParameterMapping(Orderable):
    """
    Maps a source field from an automated forecast provider (e.g. Open-Meteo)
    to one of the locally configured ForecastDataParameters.

    This replaces the previously hard-coded field maps so admins can decide,
    per provider, which API value feeds which database parameter.
    """
    parent = ParentalKey(ForecastSetting, on_delete=models.CASCADE,
                         related_name="provider_parameter_mappings")
    provider = models.CharField(max_length=50, choices=get_provider_choices(),
                                verbose_name=_("Provider"))
    source_field = models.CharField(max_length=100, verbose_name=_("Provider source field"))
    parameter = models.ForeignKey("ForecastDataParameters", on_delete=models.CASCADE,
                                  related_name="provider_mappings",
                                  verbose_name=_("Database parameter"))

    class Meta:
        ordering = ["sort_order"]
        unique_together = ("parent", "provider", "source_field")

    panels = [
        FieldPanel('provider'),
        FieldPanel('source_field', widget=ProviderFieldWidget),
        FieldPanel('parameter'),
    ]

    def __str__(self):
        return f"{self.provider}: {self.source_field} -> {self.parameter}"
