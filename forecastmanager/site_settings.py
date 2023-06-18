
from wagtail.contrib.settings.models import BaseSiteSetting
from wagtail.contrib.settings.registry import register_setting
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import (
    FieldPanel,
    TabbedInterface,
    ObjectList,
)
# @register_setting
class Setting(BaseSiteSetting):
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

    panels = [
        FieldPanel("temp_units"),
        FieldPanel("wind_units"),
    ]

    panels = [
        FieldPanel('enable_auto_forecast'),
    ]

    edit_handler = TabbedInterface([
        ObjectList([
            FieldPanel('enable_auto_forecast'),
        ], heading=_("Forecast Source")),
        ObjectList([
            FieldPanel("temp_units"),
            FieldPanel("wind_units"),
        ], heading=_("Measurement Units")),
       
    ])