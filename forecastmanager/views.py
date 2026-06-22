import csv
import json

from django.contrib import messages
from django.contrib.gis.geos import Point
from django.db import transaction
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS
from wagtail.api.v2.utils import get_full_url

from forecastmanager.models import City, Forecast
from .forecast_settings import ForecastSetting
from .forms import CityLoaderForm
from .serializers import CitySerializer, ForecastSerializer, ForecastPostSerializer
from .utils import get_weather_condition_icons


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
        # Public API serves published forecasts only; drafts await review.
        queryset = queryset.filter(status=Forecast.STATUS_PUBLISHED)
        queryset = queryset.filter(forecast_date__gte=timezone.localtime().date())
        return queryset


class ForecastPostView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ForecastPostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        forecast = serializer.save()

        response_data = {
            "message": "Forecast data pushed successfully.",
            "forecast": ForecastSerializer(forecast, context={"request": request}).data,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


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


def edit_forecast_values(request, forecast_id):
    """
    Grid editor for an existing forecast's per-city values.

    GET renders a Handsontable grid pre-filled with the current city forecasts.
    POST replaces the city forecasts in place. A city whose condition or values
    changed is marked ``manual`` (so automated runs won't overwrite it); rows
    left untouched keep their existing provenance, so auto-refresh continues for
    them. An optional "Publish after saving" flag publishes the forecast.
    """
    from .models import Forecast, CityForecast, DataValue
    from .forms import parse_forecast_table

    forecast = get_object_or_404(Forecast, pk=forecast_id)
    fm_settings = ForecastSetting.for_request(request)
    parameters = fm_settings.data_parameter_values
    param_types = {p["parameter"]: p.get("parameter_type", "numeric") for p in parameters}

    index_url = reverse(Forecast.snippet_viewset.get_url_name("list"))
    template = "forecastmanager/edit_forecast_values.html"

    def normalize(parameter_key, value):
        if param_types.get(parameter_key) == "numeric":
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        return "" if value is None else str(value)

    def build_context(error=None):
        initial_rows = []
        for city_forecast in forecast.city_forecasts.all():
            values_by_key = {
                dv.parameter.parameter: dv.parsed_value for dv in city_forecast.data_values.all()
            }
            row = [city_forecast.city.name]
            for param in parameters:
                value = values_by_key.get(param["parameter"], "")
                row.append("" if value is None else value)
            condition_repr = ""
            if city_forecast.condition:
                condition_repr = city_forecast.condition.alias or city_forecast.condition.label
            row.append(condition_repr)
            initial_rows.append(row)

        cities = [{"id": str(c.id), "name": c.name} for c in City.objects.all()]
        return {
            "forecast": forecast,
            "parameters": parameters,
            "cities": cities,
            "weather_conditions": fm_settings.weather_conditions_list,
            "initial_rows": initial_rows,
            "index_url": index_url,
            "error": error,
        }

    if request.method == "POST":
        raw = request.POST.get("data")
        publish = request.POST.get("publish") in ("on", "true", "1", "True")

        try:
            data = json.loads(raw) if raw else None
            forecast_data = parse_forecast_table(data)
        except Exception as exc:
            messages.error(request, str(exc))
            return render(request, template, build_context(error=str(exc)))

        # Snapshot existing per-city state for change detection.
        existing_state = {}
        for city_forecast in forecast.city_forecasts.all():
            values = {dv.parameter.parameter: dv.value for dv in city_forecast.data_values.all()}
            existing_state[str(city_forecast.city_id)] = {
                "condition_id": city_forecast.condition_id,
                "values": values,
                "data_source": city_forecast.data_source,
            }

        with transaction.atomic():
            if publish:
                forecast.status = Forecast.STATUS_PUBLISHED
                forecast.save(update_fields=["status"])

            forecast.city_forecasts.all().delete()

            for city_data in forecast_data:
                city = city_data["city"]
                condition = city_data["condition"]
                data_values = city_data["data_values"]

                new_values = {
                    d["parameter"].parameter: normalize(d["parameter"].parameter, d["value"])
                    for d in data_values
                }
                prev = existing_state.get(str(city.id))

                changed = True
                if prev is not None:
                    prev_values = {k: normalize(k, v) for k, v in prev["values"].items()}
                    changed = (prev["condition_id"] != condition.id) or (prev_values != new_values)

                data_source = (
                    CityForecast.DATA_SOURCE_MANUAL if changed or prev is None
                    else prev["data_source"]
                )

                city_forecast = CityForecast.objects.create(
                    parent=forecast,
                    city=city,
                    condition=condition,
                    data_source=data_source,
                )
                DataValue.objects.bulk_create([
                    DataValue(parent=city_forecast, parameter=d["parameter"], value=d["value"])
                    for d in data_values
                ])

        messages.success(request, _("Forecast values updated."))
        return redirect(index_url)

    return render(request, template, build_context())


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
    options = get_weather_condition_icons()
    icons = [{"id": icon["id"], "name": icon["name"], "url": get_full_url(request, icon["icon_url"])} for icon in
             options]
    return JsonResponse(icons, safe=False)
