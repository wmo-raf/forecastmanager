from django import template
from django.utils import timezone

from forecastmanager.models import Forecast

register = template.Library()


@register.inclusion_tag(filename="cap/active_alert.html")
def get_city_forecast_section():
    forecasts = Forecast.objects.filter(forecast_date__gte=timezone.localtime()).order_by("forecast_date")
