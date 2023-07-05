from django.urls import path, include, reverse
from wagtail.admin.menu import MenuItem
from wagtail import hooks
# from . import urls
from django.utils.html import format_html
from django.templatetags.static import static
from forecastmanager.models import City, DailyWeather
from forecastmanager.site_settings import ForecastSetting 
from django.utils.translation import gettext_lazy as _
from django.urls import path
from django.urls import re_path
from forecastmanager.views import add_forecast, save_data,get_forecast
from wagtail.contrib.modeladmin.options import (
    ModelAdmin, 
    modeladmin_register,
    ModelAdminGroup
)


@hooks.register("register_admin_urls")
def register_admin_urls():
    """
    Registers forecast urls in the wagtail admin.
    """
    return [
        # path(
        #     "forecast/",
        #     include((urls, "forecast"), namespace="forecast_admin"),
        # ),
        path("load_forecast/", get_forecast, name="load_forecast"),
        path("add_forecast/", add_forecast, name="add_forecast"),
        path('save-data/', save_data, name='save_data'),
        
    ]


class ForecastSettingAdmin(ModelAdmin):
    model = ForecastSetting
    menu_label = 'Settings'
    menu_icon = 'cog'
    add_to_settings_menu = False
    exclude_from_explorer = False

class CitiesAdmin(ModelAdmin):
    model = City
    menu_label = 'Cities'
    menu_icon = 'site'
    add_to_settings_menu = False
    exclude_from_explorer = False

class DailyWeatherAdmin(ModelAdmin):
    model = DailyWeather
    menu_label = 'Daily Weather'
    menu_icon = 'site'
    add_to_settings_menu = False
    exclude_from_explorer = False


# class ConditionCategoryAdmin(ModelAdmin):
#     model = ConditionCategory
#     menu_label = 'Weather Conditions'
#     menu_icon = 'cog'
#     add_to_settings_menu = False
#     exclude_from_explorer = False

class CityForecastGroup(ModelAdminGroup):
    menu_label = 'City Forecast'
    menu_icon = 'table'  # change as required
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (CitiesAdmin, DailyWeatherAdmin)

    def get_submenu_items(self):
        menu_items = []
        item_order = 1
        for modeladmin in self.modeladmin_instances:
            menu_items.append(modeladmin.get_menu_item(order=item_order))
            item_order += 1

            # append raster upload link
        add_forecast_item = MenuItem(label="Add Forecasts", url=reverse("add_forecast"), icon_name="plus")
        load_forecast_item = MenuItem(label="Load Forecasts", url=reverse("load_forecast"), icon_name="view")
        
        menu_items.append(add_forecast_item)
        menu_items.append(load_forecast_item)

        try:
            settings_url = reverse(
                "wagtailsettings:edit",
                args=[ForecastSetting._meta.app_label, ForecastSetting._meta.model_name, ],
            )
            gm_settings_menu = MenuItem(label=_("Settings"), url=settings_url, icon_name="cog")
            menu_items.append(gm_settings_menu)
        except Exception:
            pass

        return menu_items
    

modeladmin_register(CityForecastGroup)
