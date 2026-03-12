from django.urls import path

from .views import (
    CityListView,
    ForecastListView,
    ForecastPostView,
    download_forecast_template,
    weather_icons,
    forecast_settings
)

urlpatterns = [
    path('api/cities', CityListView.as_view(), name='cities-list'),
    path('api/forecasts', ForecastListView.as_view(), name='forecast-list'),
    path('api/forecasts/post', ForecastPostView.as_view(), name='forecast-post'),
    path('api/forecast-settings', forecast_settings, name='forecast-settings'),
    path('api/weather-icons', weather_icons, name='weather-icons'),
    path('api/forecast_template.csv', download_forecast_template, name='download-forecast-template'),
]
