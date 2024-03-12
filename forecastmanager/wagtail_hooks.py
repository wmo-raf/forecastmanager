from django.urls import reverse, path
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import (
    SnippetViewSet,
    SnippetViewSetGroup,
    CreateView,
)

from forecastmanager.forecast_settings import ForecastSetting
from forecastmanager.forms import ForecastForm
from forecastmanager.models import City, DailyWeather, Forecast
from forecastmanager.views import load_cities


@hooks.register('register_admin_urls')
def urlconf_forecastmanager():
    return [
        path('load-cities/', load_cities, name='load_cities'),
    ]


@hooks.register("register_icons")
def register_icons(icons):
    weather_parameter_icons = [
        'wagtailfontawesomesvg/solid/temperature-high.svg',
        'wagtailfontawesomesvg/solid/temperature-low.svg',
    ]

    return icons + weather_parameter_icons


class CityViewSet(SnippetViewSet):
    model = City
    list_filter = {"name": ["icontains"]}

    index_template_name = "forecastmanager/city_index.html"

    icon = "globe"
    menu_label = _("Cities")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        name = request.GET.get("name")

        print(name)

        return queryset


class DailyWeatherViewSet(SnippetViewSet):
    model = DailyWeather

    icon = 'site'
    menu_label = _('Daily Weather')


class ForecastCreateView(CreateView):
    form_class = ForecastForm
    template_name = "forecastmanager/create_forecast.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fm_settings = ForecastSetting.for_request(self.request)

        parameters = fm_settings.data_parameter_values
        cities = City.objects.all()
        cities_list = []
        for city in cities:
            cities_list.append({
                "id": str(city.id),
                "name": city.name,
            })

        weather_conditions_list = fm_settings.weather_conditions_list

        context.update({
            "cities": cities_list,
            "parameters": parameters,
            "weather_conditions": weather_conditions_list,
        })

        return context


class ForecastViewSet(SnippetViewSet):
    model = Forecast

    add_view_class = ForecastCreateView
    create_template_name = "forecastmanager/create_forecast.html"

    icon = 'table'
    menu_label = _('Daily Forecast')


class ForecastViewSetGroup(SnippetViewSetGroup):
    items = (CityViewSet, ForecastViewSet, DailyWeatherViewSet)
    menu_icon = "table"
    menu_label = _("City Forecast")
    menu_name = "city_forecast"

    def get_submenu_items(self):
        menu_items = super().get_submenu_items()

        try:
            settings_url = reverse(
                "wagtailsettings:edit",
                args=[ForecastSetting._meta.app_label, ForecastSetting._meta.model_name, ],
            )
            fm_settings_menu = MenuItem(label=_("Settings"), url=settings_url, icon_name="cog")
            menu_items.append(fm_settings_menu)
        except Exception:
            pass

        return menu_items


register_snippet(ForecastViewSetGroup)


#
@hooks.register('construct_settings_menu')
def hide_settings_menu_item(request, menu_items):
    # hide forecast setting from setting menu items.
    # Will be directly accessed from city forecast menu
    # This is to avoid crowding settings menu
    hidden_settings = ["forecast-setting"]
    menu_items[:] = [item for item in menu_items if item.name not in hidden_settings]
