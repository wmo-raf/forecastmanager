from django.urls import path, include, reverse
from wagtail.admin.menu import MenuItem
from wagtail import hooks
# from . import urls
from django.utils.html import format_html
from django.templatetags.static import static
from forecastmanager.models import City, ConditionCategory
from forecastmanager.site_settings import Setting 
from django.utils.translation import gettext_lazy as _
from django.urls import path
from django.urls import re_path
from forecastmanager.views import add_forecast, save_data, get_data
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
        path("add_forecast/", add_forecast, name="add_forecast"),
        path('save-data/', save_data, name='save_data'),
        re_path(r'^get-data/$', get_data, name='get_data'),

        
    ]


@hooks.register("insert_global_admin_css")
def insert_global_admin_css():
    return format_html(
        '<link rel="stylesheet" type="text/css" href="{}">',
        static("css/admin.css"),
    )

class SettingsAdmin(ModelAdmin):
    model = Setting
    menu_label = 'Settings'
    menu_icon = 'cog'
    add_to_settings_menu = False
    exclude_from_explorer = False

class CitiesAdmin(ModelAdmin):
    model = City
    menu_label = 'Cities'
    menu_icon = 'cog'
    add_to_settings_menu = False
    exclude_from_explorer = False

class ConditionCategoryAdmin(ModelAdmin):
    model = ConditionCategory
    menu_label = 'Weather Conditions'
    menu_icon = 'cog'
    add_to_settings_menu = False
    exclude_from_explorer = False

class CityForecastGroup(ModelAdminGroup):
    menu_label = 'City Forecast'
    menu_icon = 'table'  # change as required
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (CitiesAdmin, ConditionCategoryAdmin)

    def get_submenu_items(self):
        menu_items = []
        item_order = 1
        for modeladmin in self.modeladmin_instances:
            menu_items.append(modeladmin.get_menu_item(order=item_order))
            item_order += 1

            # append raster upload link
        upload_menu_item = MenuItem(label="Forecasts", url=reverse("add_forecast"), icon_name="cog")

        menu_items.append(upload_menu_item)

        try:
            settings_url = reverse(
                "wagtailsettings:edit",
                args=[Setting._meta.app_label, Setting._meta.model_name, ],
            )
            gm_settings_menu = MenuItem(label=_("Settings"), url=settings_url, icon_name="cog")
            menu_items.append(gm_settings_menu)
        except Exception:
            pass

        return menu_items

modeladmin_register(CityForecastGroup)