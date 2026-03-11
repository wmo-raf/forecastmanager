
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET
from django.template.loader import render_to_string
from forecastmanager.forecast_settings import ForecastSetting
from forecastmanager.models import City,CityForecast, Forecast
from forecastmanager.serializers import ForecastSerializer
from wagtail.api.v2.utils import get_full_url
from wagtail.models import Site

def get_city_forecast_detail_data(city, multi_period=False, request=None, for_home_widget=False):
    localtime = timezone.localtime()

    city_forecasts = CityForecast.objects.filter(city=city, parent__forecast_date__gte=localtime.date())

    city_forecasts_by_date = {}

    for forecast in city_forecasts:
        if multi_period and forecast.datetime < localtime:
            continue

        forecast_date = forecast.parent.forecast_date
        if forecast_date not in city_forecasts_by_date:
            city_forecasts_by_date[forecast_date] = []
        city_forecasts_by_date[forecast_date].append(forecast)
    if request:
        forecast_setting = ForecastSetting.for_request(request)
    else:
        site = Site.objects.get(is_default_site=True)
        forecast_setting = ForecastSetting.for_site(site)

    if for_home_widget:
        weather_parameters = forecast_setting.data_parameters.filter(show_on_home_widget=True)[:4]
    else:
        weather_parameters = forecast_setting.data_parameters.all()

    return {
        "city_forecasts_by_date": city_forecasts_by_date,
        "weather_parameters": weather_parameters,
    }


@require_GET
def get_home_forecast_widget(request):
    forecast_setting = ForecastSetting.for_request(request)
    
    city_slug = request.GET.get('city')
    context = {}
    
    
    if city_slug:
        city = City.objects.filter(slug=city_slug).first()
        if city is None:
            context.update({
                "error": True,
                "error_message": _("Location not found. Please search for a different location.")
            })
            return JsonResponse(context, status=404)
    else:
        city = forecast_setting.default_city
        if not city:
            city = City.objects.first()
    
    if city is None:
        context.update({
            "error": True,
            "error_message": _("No location set in the system. Please contact the administrator."),
        })
        
        return render(request, 'home/widgets/location_forecast_single_slider.html', context)
    
    city_detail_page = forecast_setting.weather_detail_page
    
    if city_detail_page:
        # Try getting the city detail page URL. If it fails, ignore it.
        # this is here because a different page than what is expected might be set
        try:
            city_detail_page = city_detail_page.specific
            city_detail_page_url = city_detail_page.get_full_url(request) + city_detail_page.reverse_subpage(
                "daily_table_for_city", kwargs={"city_slug": city.slug})
            context.update({
                "city_detail_page_url": city_detail_page_url,
            })
        except Exception:
            pass
    
    city_search_url = get_full_url(request, reverse("cities-list"))
    context.update({
        "city_search_url": city_search_url,
    })
    
    if forecast_setting.weather_reports_page:
        context.update({
            "weather_reports_page_url": forecast_setting.weather_reports_page.get_full_url(request)
        })
    
    response = None
    
    if response is None:
        forecast_periods_count = forecast_setting.periods.count()
        
        multi_period = forecast_periods_count > 1
        
        data = get_city_forecast_detail_data(city, multi_period=multi_period, request=request,
                                             for_home_widget=True)
        
        context.update({
            "city": city,
            "show_condition_label": forecast_setting.show_conditions_label_on_widget,
            "use_period_labels": forecast_setting.use_period_labels,
            **data,
        })
        
        if multi_period:
            response = render(request, 'home/widgets/location_forecast_multiple_slider.html', context)
        else:
            response = render(request, 'home/widgets/location_forecast_single_slider.html', context)
        
    
    return response

