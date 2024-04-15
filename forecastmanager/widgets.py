import json

from django.forms import widgets, TextInput
from django.templatetags.static import static
from wagtail.telepath import register
from wagtail.utils.widgets import WidgetWithScript
from wagtail.widget_adapters import WidgetAdapter

from forecastmanager.constants import WEATHER_CONDITION_ICONS, WEATHER_PARAMETER_CHOICES


class WeatherSymbolChooserWidget(WidgetWithScript, widgets.TextInput):
    template_name = "forecastmanager/weather_symbol_chooser_widget.html"

    def __init__(self, attrs=None):
        default_attrs = {
            "class": "symbol-chooser-widget__icon-input",
        }
        attrs = attrs or {}
        attrs = {**default_attrs, **attrs}
        super().__init__(attrs=attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if value:
            context["widget"]["icon_url"] = static("forecastmanager/weathericons/{0}.png".format(value))
        return context

    def render_js_init(self, id_, name, value):
        options = WEATHER_CONDITION_ICONS
        return "$(document).ready(() => new WeatherSymbolChooserWidget({0},{1}));".format(json.dumps(id_),
                                                                                          json.dumps(options))

    class Media:
        css = {
            "all": [
                "forecastmanager/css/weather-symbol-chooser-widget.css",
            ]
        }
        js = [
            "forecastmanager/js/weather-symbol-chooser-widget.js",
        ]


class WeatherSymbolWidgetAdapter(WidgetAdapter):
    js_constructor = "forecastmanager.widgets.WeatherSymbolChooserWidget"

    class Media:
        js = [
            "forecastmanager/js/weather-symbol-chooser-widget-telepath.js",
        ]


register(WeatherSymbolWidgetAdapter(), WeatherSymbolChooserWidget)


class DataParameterWidget(WidgetWithScript, TextInput):
    template_name = "forecastmanager/forecast_data_parameter_widget.html"

    def __init__(self, attrs=None, **kwargs):
        default_attrs = {}

        if attrs:
            default_attrs.update(attrs)

        super().__init__(default_attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        options = []

        for choice in WEATHER_PARAMETER_CHOICES:
            options.append({
                "value": choice[0],
                "label": choice[1],
            })

        context["widget"].update({
            "parameter_list": options
        })

        return context

    def render_js_init(self, id_, name, value):
        return "new DataParameterWidget({0},{1});".format(json.dumps(id_), json.dumps(value))

    class Media:
        js = [
            "forecastmanager/js/forecast-data-parameter-widget.js",
        ]
