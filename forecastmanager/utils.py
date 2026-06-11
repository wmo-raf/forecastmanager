from django.templatetags.static import static

from .constants import WEATHER_CONDITIONS


def get_weather_condition_icons(ext="png"):
    # ext="svg" -> animated icons for HTML <img> contexts (e.g. admin chooser).
    # ext="png" -> raster icons for map use; MapLibre/Mapbox loadImage only
    #              accepts raster images, so the map must use PNG.
    icons = [
        {"value": condition["id"], **condition,
         'icon_url': static("forecastmanager/weathericons/{0}.{1}".format(condition["id"], ext))} for condition in
        WEATHER_CONDITIONS
    ]

    return icons
