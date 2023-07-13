from django.urls import path

from .views import CityListView, ForecastListView, save_forecast_data

urlpatterns = [
    path('api/save-forecast', save_forecast_data, name='save-forecast-data'),
    path('api/forecasts', ForecastListView.as_view(), name='forecast-list'),
    path('api/cities', CityListView.as_view(), name='cities-list'),
]
