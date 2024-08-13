from django.templatetags.static import static

from .constants import WEATHER_CONDITIONS


def get_weather_condition_icons():
    icons = [
        {"value": condition["id"], **condition,
         'icon_url': static("forecastmanager/weathericons/{0}.png".format(condition["id"]))} for condition in
        WEATHER_CONDITIONS
    ]

    return icons
