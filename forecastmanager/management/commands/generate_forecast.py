import logging

import requests
from dateutil.parser import parse
from django.core.management.base import BaseCommand
from django.utils import timezone
from wagtail import hooks
from wagtail.models import Site

from forecastmanager.constants import WEATHER_CONDITIONS_AS_DICT
from forecastmanager.forecast_settings import (
    ForecastSetting,
    WeatherCondition,
    ForecastPeriod,
    ForecastDataParameters
)
from forecastmanager.models import (
    City,
    CityForecast,
    DataValue,
    Forecast
)

logger = logging.getLogger(__name__)

# Define the base URL for the Met Norway API
BASE_URL = "https://api.met.no/weatherapi/locationforecast/2.0/complete"

DEFAULT_INSTANT_DATA_PARAMETERS = [
    {"parameter": "air_pressure_at_sea_level", "name": "Air Pressure (Sea level)", "parameter_unit": "hPa"},
    {"parameter": "air_temperature", "name": "Minimum Air Temperature", "parameter_unit": "°C"},
    {"parameter": "wind_speed", "name": "Wind Speed", "parameter_unit": "m/s"},
    {"parameter": "wind_from_direction", "name": "Wind Direction ", "parameter_unit": "degrees"}
]

DEFAULT_NEXT_HOURS_DATA_PARAMETERS = [
    {"parameter": "air_temperature_min", "name": "Minimum Air Temperature", "parameter_unit": "°C"},
    {"parameter": "air_temperature_max", "name": "Maximum Air Temperature", "parameter_unit": "°C"},
    {"parameter": "precipitation_amount", "name": "Precipitation Amount", "parameter_unit": "mm"},
]

DEFAULT_PARAMETERS = DEFAULT_INSTANT_DATA_PARAMETERS + DEFAULT_NEXT_HOURS_DATA_PARAMETERS


class Command(BaseCommand):
    help = ('Get the weather forecast for the next 7 days from Yr.no '
            'for all cities in the database and save it to the database.')

    def handle(self, *args, **options):
        logger.info("Getting 7 Day Forecast from Yr.no...")

        cities = City.objects.all()
        if not cities:
            logger.error("No cities found")
            return

        site = Site.objects.get(is_default_site=True)

        if not site:
            logger.error("No default site found")
            return

        forecast_setting = ForecastSetting.for_site(site)

        site_name = site.site_name
        root_url = site.root_url

        user_agent = f"ClimWeb {root_url}"
        if site_name:
            user_agent = f"{site_name}/{user_agent}"

        user_agent = user_agent.strip()

        if not forecast_setting.enable_auto_forecast:
            logger.error("Auto forecast is disabled")
            return

        conditions = forecast_setting.weather_conditions.all()
        conditions_by_symbol = {condition.symbol: condition for condition in conditions}

        parameters = forecast_setting.data_parameters.all()

        if not parameters.exists():
            # create default forecast parameters
            for default_parameter in DEFAULT_PARAMETERS:
                ForecastDataParameters.objects.create(parent=forecast_setting, **default_parameter)

            parameters = forecast_setting.data_parameters.all()

        parameters_dict = {parameter.parameter: parameter for parameter in parameters}

        cities_data = {}

        for city in cities:
            logger.info(f"Getting forecast for {city.name}...")

            lon = city.x
            lat = city.y

            url = f"{BASE_URL}?lat={lat}&lon={lon}"

            # Send a GET request to the API
            response = requests.get(url, headers={"User-Agent": user_agent})

            if response.status_code >= 400:
                logger.error(f"Failed to get forecast for {city.name}. Status code: {response.status_code}")
                continue

            # Get the weather data from the response
            data = response.json()

            # Get the timeseries data from the response
            timeseries = data.get('properties', {}).get('timeseries')

            # Get the first and last datetime for the forecast
            first_datetime = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
            max_days = 6
            last_datetime = (first_datetime + timezone.timedelta(days=max_days)).replace(hour=23, minute=59, second=59)

            # Create a forecast for the city
            for time_data in timeseries:
                time = time_data.get("time")
                utc_date = parse(time)
                timezone_date = timezone.localtime(utc_date)

                # Check if the forecast is within the next 7 days
                if timezone_date < first_datetime or timezone_date > last_datetime:
                    continue

                data_values = time_data.get("data", {})

                # Get the weather condition for the forecast
                condition = data_values.get("next_1_hours", {}).get("summary", {}).get("symbol_code")
                if condition is None:
                    condition = data_values.get("next_6_hours", {}).get("summary", {}).get("symbol_code")

                if conditions_by_symbol.get(condition) is None:
                    condition_info = WEATHER_CONDITIONS_AS_DICT.get(condition)

                    if condition_info is None:
                        continue

                    label = condition_info.get('name')
                    created_condition = WeatherCondition.objects.create(parent=forecast_setting, symbol=condition,
                                                                        label=label)
                    conditions_by_symbol[created_condition.symbol] = created_condition

                condition_obj = conditions_by_symbol.get(condition)

                if condition_obj is None:
                    logger.warning(f"Cannot find or create condition for symbol code: {condition}")
                    continue

                city_forecast = CityForecast(city=city, condition=condition_obj)

                instant_data = data_values.get("instant", {}).get("details", {})
                # Add the instant data values to the forecast
                for key, value in instant_data.items():
                    if parameters_dict.get(key) is None:
                        continue

                    parameter = parameters_dict[key]
                    data_value = DataValue(parameter=parameter, value=value)
                    city_forecast.data_values.add(data_value)

                # Add the next hours data values to the forecast
                for param in DEFAULT_NEXT_HOURS_DATA_PARAMETERS:
                    param_key = param.get("parameter")
                    if parameters_dict.get(param_key) is None:
                        continue

                    next_1_hours_data = data_values.get("next_1_hours", {}).get("details", {})
                    next_6_hours_data = data_values.get("next_6_hours", {}).get("details", {})

                    next_data_value = None
                    if param_key in next_1_hours_data:
                        next_data_value = DataValue(parameter=parameters_dict[param_key],
                                                    value=next_1_hours_data[param_key])
                    elif param_key in next_6_hours_data:
                        next_data_value = DataValue(parameter=parameters_dict[param_key],
                                                    value=next_6_hours_data[param_key])

                    if next_data_value is not None:
                        city_forecast.data_values.add(next_data_value)

                # Add the forecast to the cities data
                if timezone_date in cities_data:
                    cities_data[timezone_date].append(city_forecast)
                else:
                    cities_data[timezone_date] = [city_forecast]

        created_forecast_pks = []

        # Create the forecast for the cities
        for forecast_date, city_forecasts in cities_data.items():
            effective_time = f"{forecast_date.hour}:00"

            forecast_period = ForecastPeriod.objects.filter(forecast_effective_time=effective_time).first()
            if forecast_period is None:
                forecast_period = ForecastPeriod.objects.create(parent=forecast_setting,
                                                                forecast_effective_time=effective_time,
                                                                label=effective_time)

            forecast = Forecast.objects.filter(forecast_date=forecast_date, effective_period=forecast_period)
            if forecast.exists():
                forecast.delete()

            forecast = Forecast(forecast_date=forecast_date, effective_period=forecast_period, source="yr")

            for city_forecast in city_forecasts:
                forecast.city_forecasts.add(city_forecast)

            forecast.save()

            # Add the forecast to the list of created forecasts
            created_forecast_pks.append(forecast.pk)

        for fn in hooks.get_hooks("after_generate_forecast"):
            fn(created_forecast_pks)
