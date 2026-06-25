from django.urls import path

from .views import (
    CityListView,
    ForecastListView,
    ForecastPostView,
    MobileForecastView,
    ForecastSettingsView,
    WeatherIconsView,
    download_forecast_template,
)

urlpatterns = [
    path('api/cities', CityListView.as_view(), name='cities-list'),
    path('api/forecasts', ForecastListView.as_view(), name='forecast-list'),
    path('api/forecast_mobile', MobileForecastView.as_view(), name='forecast-mobile'),
    path('api/forecasts/post', ForecastPostView.as_view(), name='forecast-post'),
    path('api/forecast-settings', ForecastSettingsView.as_view(), name='forecast-settings'),
    path('api/weather-icons', WeatherIconsView.as_view(), name='weather-icons'),
    path('api/forecast_template.csv', download_forecast_template, name='download-forecast-template'),
]
