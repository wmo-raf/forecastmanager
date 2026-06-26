import csv
import json

from django.contrib import messages
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db import transaction
from django.http import HttpResponse
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

from forecastmanager.models import City, CityForecast, Forecast
from .forecast_settings import ForecastSetting
from .forms import CityLoaderForm, GeoNamesImportForm
from .services.geonames import (
    GeoNamesClient,
    GeoNamesError,
    GeoNamesImportService,
)
from .serializers import (
    CitySerializer,
    ForecastSerializer,
    ForecastPostSerializer,
    MobileForecastTimeserieSerializer,
)
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


class MobileForecastView(APIView):
    """
    GET /api/forecast_mobile?lat=<lat>&lon=<lon>

    Returns a Met Norway-style (api.met.no/locationforecast) feature for the
    city nearest to the supplied coordinates. Each timeseries step carries only
    ``time``, the ``instant`` data values, and the ``next_1_hours`` weather
    ``symbol_code``. Only published, current/future forecasts are served.
    """

    permission_classes = [IsAuthenticated | ReadOnly]

    def get(self, request, *args, **kwargs):
        lat = request.query_params.get("lat")
        lon = request.query_params.get("lon")

        if lat is None or lon is None:
            return Response(
                {"detail": "lat and lon query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            return Response(
                {"detail": "lat and lon must be valid numbers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Match the request to the nearest stored city (PostGIS distance sort).
        point = Point(x=lon, y=lat, srid=4326)
        city = (
            City.objects.annotate(distance=Distance("location", point))
            .order_by("distance")
            .first()
        )

        if city is None:
            return Response(
                {"detail": "No cities available to match."},
                status=status.HTTP_404_NOT_FOUND,
            )

        city_forecasts = (
            CityForecast.objects.filter(
                city=city,
                parent__status=Forecast.STATUS_PUBLISHED,
                parent__forecast_date__gte=timezone.localtime().date(),
            )
            .select_related("parent", "parent__effective_period", "condition")
            .prefetch_related("data_values__parameter")
            .order_by(
                "parent__forecast_date",
                "parent__effective_period__forecast_effective_time",
            )
        )

        # Units for each parameter present in the served timeseries.
        units = {}
        for city_forecast in city_forecasts:
            for data_value in city_forecast.data_values.all():
                parameter = data_value.parameter
                units.setdefault(parameter.parameter, parameter.units)

        # Did the request land exactly on the city, or is this the nearest one?
        city_lon, city_lat = city.coordinates
        is_exact = abs(city_lon - lon) < 1e-4 and abs(city_lat - lat) < 1e-4
        location_source = "exact" if is_exact else "nearest"

        timeseries = MobileForecastTimeserieSerializer(city_forecasts, many=True).data

        return Response(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": city.coordinates,
                },
                "properties": {
                    "meta": {
                        "updated_at": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "city": city.name,
                        "location_source": location_source,
                        "location_description": (
                            f"Forecast for the exact city ({city.name})."
                            if is_exact
                            else f"Forecast for the nearest city ({city.name})."
                        ),
                        "units": units,
                    },
                    "timeseries": timeseries,
                },
            }
        )


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


def import_geonames_cities(request):
    """
    Admin page to import cities from the GeoNames web service.

    Submitting with action=preview fetches and lists the cities that would be
    imported (admin seats + highest-population places, capped at the chosen
    maximum). Submitting with action=import persists them. A GeoNames username
    must be configured under Forecast Settings > Other Settings.
    """
    template = "forecastmanager/import_geonames_cities.html"
    index_url = reverse(City.snippet_viewset.get_url_name("list"))
    fm_settings = ForecastSetting.for_request(request)
    username = fm_settings.geonames_username

    context = {"index_url": index_url}

    if request.method != "POST":
        context["form"] = GeoNamesImportForm()
        return render(request, template, context)

    form = GeoNamesImportForm(request.POST)
    if not form.is_valid():
        context["form"] = form
        return render(request, template, context)

    if not username:
        form.add_error(
            None,
            _("Set a GeoNames username under Forecast Settings > Other Settings before importing."),
        )
        context["form"] = form
        return render(request, template, context)

    country = form.cleaned_data["country"]
    max_cities = form.cleaned_data["max_cities"]
    overwrite = form.cleaned_data["overwrite_existing"]
    action = request.POST.get("action", "preview")

    service = GeoNamesImportService(
        GeoNamesClient(username=username),
        max_cities=max_cities,
    )

    try:
        places, result = service.run(
            country=country,
            overwrite=overwrite,
            dry_run=(action != "import"),
        )
    except GeoNamesError as exc:
        form.add_error(None, str(exc))
        context["form"] = form
        return render(request, template, context)

    if action == "import":
        messages.success(
            request,
            _("Imported %(created)d new and updated %(updated)d cities (%(skipped)d skipped).")
            % {
                "created": result.created,
                "updated": result.updated,
                "skipped": result.skipped,
            },
        )
        return redirect(index_url)

    context.update({
        "form": form,
        "places": places,
        "preview": True,
    })
    return render(request, template, context)


class ForecastSettingsView(APIView):
    permission_classes = [IsAuthenticated | ReadOnly]

    def get(self, request, *args, **kwargs):
        fm_settings = ForecastSetting.for_request(request)
        data = {
            "parameters": fm_settings.data_parameter_values,
            "periods": fm_settings.effective_periods,
        }
        return Response(data)


class WeatherIconsView(APIView):
    permission_classes = [IsAuthenticated | ReadOnly]

    def get(self, request, *args, **kwargs):
        options = get_weather_condition_icons()
        icons = [
            {
                "id": icon["id"],
                "name": icon["name"],
                "url": get_full_url(request, icon["icon_url"]),
            }
            for icon in options
        ]
        return Response(icons)
