
from django.urls import path,include
from .views import CityAPIView, ForecastAPIView
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'cities', CityAPIView)
router.register(r'forecasts', ForecastAPIView)


urlpatterns = [
    path('api/', include(router.urls)),
]