from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.api.v2.utils import get_full_url
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.models import Page

from forecastmanager.forecast_settings import ForecastSetting
from forecastmanager.models import City, CityForecast


class HomePage(Page):
    banner_image = models.ForeignKey("wagtailimages.Image", on_delete=models.SET_NULL, null=True, blank=False,
                                     related_name="+", verbose_name=_("Banner Image"))

    content_panels = Page.content_panels + [
        FieldPanel("banner_image"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        fm_settings = ForecastSetting.for_request(request)
        city_detail_page = fm_settings.weather_detail_page
        city_detail_page_url = None

        if city_detail_page:
            city_detail_page = city_detail_page.specific
            city_detail_page_url = city_detail_page.get_full_url(request)
            city_detail_page_url = city_detail_page_url + city_detail_page.reverse_subpage("forecast_for_city")
            context.update({
                "city_detail_page_url": city_detail_page_url,
            })

        city_search_url = get_full_url(request, reverse("cities-list"))
        context.update({
            "city_search_url": city_search_url,
            "city_detail_page_url": city_detail_page_url
        })

        default_city = fm_settings.default_city
        if not default_city:
            default_city = City.objects.first()

        if default_city:
            default_city_forecasts = CityForecast.objects.filter(
                city=default_city,
                parent__forecast_date__gte=timezone.localtime()
            ).order_by("parent__forecast_date")

            context.update({
                "default_city_forecasts": default_city_forecasts
            })

        return context


class WeatherPage(RoutablePageMixin, Page):
    template = "home/weather_page.html"

    @path('daily-table/')
    @path('daily-table/<str:city_name>/')
    def forecast_for_city(self, request, city_name=None):
        if city_name:
            city_name = city_name.replace("--", " ")
            city = City.objects.filter(name__iexact=city_name).first()
            if city is None:
                return self.render(request, context_overrides={
                    "error": True,
                    "error_message": "City not found"
                })
        else:
            fm_settings = ForecastSetting.for_request(request)
            city = fm_settings.default_city
            if not city:
                city = City.objects.first()

        if city is None:
            return self.render(request, context_overrides={
                "error": True,
                "error_message": "No city in database"
            })

        city_forecasts = CityForecast.objects.filter(
            city=city,
            parent__forecast_date__gte=timezone.localtime()
        )

        city_forecasts_by_date = {}
        for forecast in city_forecasts:
            forecast_date = forecast.parent.forecast_date
            if forecast_date not in city_forecasts_by_date:
                city_forecasts_by_date[forecast_date] = []
            city_forecasts_by_date[forecast_date].append(forecast)

        weather_parameters = ForecastSetting.for_request(request).data_parameters.all()

        return self.render(request, context_overrides={
            "city_forecasts_by_date": city_forecasts_by_date,
            "weather_parameters": weather_parameters,
            "city": city
        })
