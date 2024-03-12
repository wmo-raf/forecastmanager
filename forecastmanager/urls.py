from django.urls import path

from .views import CityListView, ForecastListView, download_forecast_template

urlpatterns = [
    path('api/cities', CityListView.as_view(), name='cities-list'),
    path('api/forecasts', ForecastListView.as_view(), name='forecast-list'),
    path('api/forecast_templace.csv', download_forecast_template, name='download-forecast-template'),
]
