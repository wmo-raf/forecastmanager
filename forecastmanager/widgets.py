import json

from django.forms import widgets, TextInput, Media
from django.templatetags.static import static
from wagtail.telepath import register
from wagtail.widget_adapters import WidgetAdapter

from .constants import WEATHER_PARAMETER_CHOICES
from .utils import get_weather_condition_icons


class WeatherSymbolChooserWidget(widgets.TextInput):
    template_name = "forecastmanager/weather_symbol_chooser_widget.html"
    
    def __init__(self, attrs=None):
        default_attrs = {
            "class": "symbol-chooser-widget__icon-input",
        }
        attrs = attrs or {}
        attrs = {**default_attrs, **attrs}
        super().__init__(attrs=attrs)
    
    def build_attrs(self, *args, **kwargs):
        attrs = super().build_attrs(*args, **kwargs)
        attrs['data-controller'] = 'weather-symbol-chooser-widget'
        
        options = get_weather_condition_icons()
        
        attrs['data-options'] = json.dumps(options)
        
        return attrs
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if value:
            context["widget"]["icon_url"] = static("forecastmanager/weathericons/{0}.png".format(value))
        return context
    
    @property
    def media(self):
        css = {
            "all": [
                "forecastmanager/css/weather-symbol-chooser-widget.css",
            ]
        }
        js = [
            "forecastmanager/js/weather-symbol-chooser-widget.js",
            "forecastmanager/js/weather-symbol-chooser-widget-controller.js",
        ]
        
        return Media(js=js, css=css)


class WeatherSymbolWidgetAdapter(WidgetAdapter):
    js_constructor = "forecastmanager.widgets.WeatherSymbolChooserWidget"
    
    class Media:
        js = [
            "forecastmanager/js/weather-symbol-chooser-widget-telepath.js",
        ]


register(WeatherSymbolWidgetAdapter(), WeatherSymbolChooserWidget)


class DataParameterWidget(TextInput):
    template_name = "forecastmanager/forecast_data_parameter_widget.html"
    
    def __init__(self, attrs=None, **kwargs):
        default_attrs = {}
        
        if attrs:
            default_attrs.update(attrs)
        
        super().__init__(default_attrs)
    
    def build_attrs(self, *args, **kwargs):
        attrs = super().build_attrs(*args, **kwargs)
        attrs['data-controller'] = 'data-parameter-widget'
        
        return attrs
    
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
    
    @property
    def media(self):
        js = [
            "forecastmanager/js/data-parameter-widget.js",
        ]
        
        return Media(js=js)
