import csv
from datetime import date

from django.contrib.gis.geos import Point
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS
from wagtail.api.v2.utils import get_full_url

from forecastmanager.models import City, Forecast
from .constants import WEATHER_CONDITION_ICONS
from .forecast_settings import ForecastSetting
from .forms import CityLoaderForm
from .serializers import CitySerializer, ForecastSerializer


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class CityListView(ListAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = [IsAuthenticated | ReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class ForecastListView(ListAPIView):
    queryset = Forecast.objects.all()
    serializer_class = ForecastSerializer
    filter_backends = [DjangoFilterBackend]
    permission_classes = [IsAuthenticated | ReadOnly]
    filterset_fields = ["forecast_date", "effective_period"]

    def get_queryset(self):
        queryset = super().get_queryset()
        forecast_date = self.request.query_params.get('forecast_date')

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        effective_time = self.request.query_params.get('effective_time')

        if effective_time:
            queryset = queryset.filter(effective_period__forecast_effective_time=effective_time)
        else:
            queryset = queryset.filter(effective_period__default=True)

        if start_date:
            queryset = queryset.filter(forecast_date__gte=start_date)
        else:
            queryset = queryset.filter(forecast_date__gte=date.today())

        if end_date:
            queryset = queryset.filter(forecast_date__lte=end_date)

        if forecast_date:
            queryset = queryset.filter(forecast_date=forecast_date)

        return queryset.order_by('forecast_date', 'effective_period__forecast_effective_time')


def download_forecast_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="forecast_template.csv"'

    row = ["City"]
    fm_settings = ForecastSetting.for_request(request)
    parameters = fm_settings.data_parameter_values
    parameters = [param['name'] for param in parameters]
    row.extend(parameters)
    row.append("Condition")

    writer = csv.writer(response)
    writer.writerow(row)

    cities = City.objects.all()
    for city in cities:
        row = [city.name]
        for _ in parameters:
            row.append("")
        row.append("")
        writer.writerow(row)

    return response


def load_cities(request):
    template = "forecastmanager/load_cities.html"
    context = {}

    index_url_name = City.snippet_viewset.get_url_name("list")
    index_url = reverse(index_url_name)

    if request.POST:
        form = CityLoaderForm(request.POST, files=request.FILES)

        if form.is_valid():
            cities = form.cleaned_data.get("data")
            overwrite = form.cleaned_data.get("overwrite_existing")

            for city in cities:
                city_name = city.get("city")
                lat = city.get("lat")
                lon = city.get("lon")

                exists = City.objects.filter(name__iexact=city_name).exists()

                if exists:
                    if not overwrite:
                        form.add_error(None, f"City {city_name} already exists. "
                                             f"Please check the overwrite option to update or delete the existing city.")
                        context.update({"form": form})
                        return render(request, template_name=template, context=context)
                    else:
                        city_obj = City.objects.get(name__iexact=city_name)
                        city_obj.location = Point(x=lon, y=lat, srid=4326)
                        city_obj.save()
                else:
                    city_obj = City(name=city_name, location=Point(x=lon, y=lat, srid=4326))
                    city_obj.save()

            return redirect(index_url)
        else:
            context.update({"form": form})
            return render(request, template_name=template, context=context)
    form = CityLoaderForm()
    context.update({"form": form})

    return render(request, template_name=template, context=context)


def forecast_settings(request):
    context = {}

    fm_settings = ForecastSetting.for_request(request)
    data_parameters = fm_settings.data_parameter_values
    effective_periods = fm_settings.effective_periods

    context.update({"parameters": data_parameters, "periods": effective_periods})

    return JsonResponse(context)


def weather_icons(request):
    options = WEATHER_CONDITION_ICONS
    icons = [{"id": icon["id"], "name": icon["name"], "url": get_full_url(request, icon["icon_url"])} for icon in
             options]
    return JsonResponse(icons, safe=False)
