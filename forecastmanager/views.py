import json
from datetime import date

from django.core import serializers
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS

from forecastmanager.models import City, Forecast
from .forms import ForecastForm
from .serializers import CitySerializer, ForecastSerializer
from .site_settings import ForecastSetting, ForecastPeriod


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class CityListView(ListAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = [IsAuthenticated | ReadOnly]


class ForecastListView(ListAPIView):
    queryset = Forecast.objects.all()
    serializer_class = ForecastSerializer
    filter_backends = [DjangoFilterBackend]
    permission_classes = [IsAuthenticated | ReadOnly]
    filterset_fields = ["forecast_date", "effective_period", "effective_period__whole_day", "city__id"]

    def get_serializer(self, *args, **kwargs):
        # Override the get_serializer method to handle list input
        kwargs['context'] = self.get_serializer_context()
        if isinstance(kwargs.get('data', {}), list):
            # If the input data is a list, use the many=True flag
            kwargs['many'] = True
        return self.serializer_class(*args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        forecast_date = self.request.query_params.get('forecast_date')

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(forecast_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(forecast_date__lte=end_date)

        if forecast_date:
            queryset = queryset.filter(forecast_date=forecast_date)

        return queryset.order_by('forecast_date', 'effective_period__forecast_effective_time')


def add_forecast(request):
    cities = City.objects.all()
    fm_setting = ForecastSetting.for_request(request)
    weather_conditions = fm_setting.weather_conditions.all()
    effective_periods = fm_setting.periods_as_choices

    context = {
        "city_ls": serializers.serialize('json', cities, fields=('name', 'id')),
        "weather_condition_ls": json.dumps([x.alias if x.alias else x.label for x in weather_conditions]),
        "data_parameter_values": fm_setting.data_parameter_values,
        "forecast_periods": fm_setting.periods
    }

    if request.method == 'POST':
        form = ForecastForm(request.POST, effective_periods=effective_periods)
        if form.is_valid():
            forecast_date = form.cleaned_data.get('forecast_date')
            forecast_effective_period = form.cleaned_data.get('forecast_effective_period')
            data = form.cleaned_data.get('data')
            # Do something with the data
            return JsonResponse({'message': 'Data received'}, status=200, safe=False)
        else:
            return JsonResponse({'error': 'Error occurred'}, status=400, safe=False)

    form = ForecastForm(effective_periods=effective_periods)
    context.update({"form": form})

    return render(request, "forecastmanager/create_forecast.html", context)


@csrf_exempt
def save_forecast_data(request):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    forecast_setting = ForecastSetting.for_request(request)
    parameters = forecast_setting.data_parameter_values
    weather_conditions = forecast_setting.weather_conditions.all()
    weather_conditions_by_alias_label = {x.alias if x.alias else x.label: x for x in weather_conditions}

    res_message = None

    if request.method == 'POST' and is_ajax:
        data = json.load(request)

        if data and len(data) > 0:

            records_to_create = []
            records_to_update = []

            # Iterate through the data and create or update Parent and Child objects
            try:
                for row in data:
                    city_id = row.get("city")
                    effective_period_id = row.get("effective_period")
                    forecast_date = row.get("forecast_date")
                    condition = row.get("condition")

                    if condition and condition in weather_conditions_by_alias_label:
                        condition = weather_conditions_by_alias_label.get(condition)
                    else:
                        return JsonResponse({'error': 'Error occurred'}, status=400, safe=False)

                    # Get city
                    city = City.objects.filter(pk=city_id)

                    if city.exists:
                        city = city.first()
                    else:
                        city = None

                    # Get period
                    effective_period = ForecastPeriod.objects.get(pk=effective_period_id)
                    if city and effective_period and forecast_date:
                        data_value = {}

                        for param in parameters:
                            param_name = param.get("parameter")
                            param_value = row.get(param_name)
                            if param_value:
                                data_value[param_name] = param_value

                        record = {
                            "city": city,
                            "forecast_date": forecast_date,
                            "effective_period": effective_period,
                            "condition": condition,
                            "data_value": {**data_value}
                        }

                        # check if record exists
                        existing_record = Forecast.objects.filter(city=city, forecast_date=forecast_date,
                                                                  effective_period=effective_period)

                        if len(existing_record) > 0 and existing_record.exists():
                            existing_record = existing_record.first()

                            record.update({"pk": existing_record.pk})

                            records_to_update.append(record)
                        else:

                            records_to_create.append(record)

            except Exception as e:
                return JsonResponse({'error': 'Error occurred'}, status=400, safe=False)

            # bulk create or update. Saves database round trips
            try:
                # update

                if records_to_update:
                    Forecast.objects.bulk_update(
                        [
                            Forecast(pk=values.get("pk"), condition=values.get("condition"),
                                     data_value=values.get("data_value"))
                            for values in records_to_update
                        ],
                        ["condition", "data_value"],
                        batch_size=1000
                    )
                    res_message = "Data Successfully updated"
                    # return JsonResponse({'success': True, 'message':'Data Successfully updated'})

                # create
                if records_to_create:
                    Forecast.objects.bulk_create(
                        [Forecast(**values) for values in records_to_create], batch_size=1000
                    )

                    res_message = "Data Successfully saved"

                return JsonResponse({'success': True, 'message': res_message})
            except Exception as e:
                print(e)
                return JsonResponse({'error': 'Error occurred'}, status=400, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400, safe=False)


def view_forecast(request):
    forecast_setting = ForecastSetting.for_request(request)

    dates_ls = Forecast.objects.filter(forecast_date__gte=date.today()).order_by('forecast_date').values_list(
        'forecast_date', flat=True).distinct()

    return render(request, "forecastmanager/view_forecast.html", {
        'forecast_dates': dates_ls,
        "data_parameter_values": forecast_setting.data_parameter_values,
        "forecast_periods": forecast_setting.periods
    })
