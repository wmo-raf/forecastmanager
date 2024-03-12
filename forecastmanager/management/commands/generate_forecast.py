import logging

import requests
from dateutil.parser import parse
from django.core.management.base import BaseCommand
from wagtail.models import Site

from forecastmanager.forecast_settings import ForecastSetting, WeatherCondition, ForecastPeriod
from forecastmanager.models import City, CityForecast, DataValue, Forecast
from forecastmanager.constants import WEATHER_CONDITIONS_AS_DICT

logger = logging.getLogger(__name__)

# Define the base URL for the Met Norway API
BASE_URL = "https://www.yr.no/api/v0/locations"


class Command(BaseCommand):
    help = ('Get the weather forecast for the next 7 days from Yr.no '
            'for all cities in the database and save it to the database.')

    def handle(self, *args, **options):
        print("Getting 7 Day Forecast from Yr.no...")

        cities = City.objects.all()
        if not cities:
            logger.error("No cities found")
            return

        site = Site.objects.get(is_default_site=True)

        if not site:
            logger.error("No default site found")
            return

        forecast_setting = ForecastSetting.for_site(site)

        user_agent = f"{site.site_name} (WMO NMHSs Website Template) {site.root_url}"
        user_agent = user_agent.strip()

        if not forecast_setting.enable_auto_forecast:
            logger.error("Auto forecast is disabled")
            return

        conditions = forecast_setting.weather_conditions.all()
        conditions_by_symbol = {condition.symbol: condition for condition in conditions}

        parameters = forecast_setting.data_parameters.all()
        parameters_dict = {parameter.parameter: parameter for parameter in parameters}

        forecast_periods = forecast_setting.periods.all()
        if not forecast_periods.exists():
            # create default forecast period
            ForecastPeriod.objects.create(parent=forecast_setting,
                                          label="Whole Day",
                                          forecast_effective_time="00:00:00",
                                          default=True)

        forecast_period = forecast_periods.filter(default=True).first()
        if not forecast_period:
            # pick first one if no default
            forecast_period = forecast_periods.first()

        cities_data = {}

        for city in cities:
            print(f"Getting forecast for {city.name}...")

            lon = city.x
            lat = city.y

            url = f"{BASE_URL}/{lat},{lon}/forecast"

            # Send a GET request to the API
            response = requests.get(url, headers={"User-Agent": user_agent})

            if response.status_code >= 400:
                logger.error(
                    f"Failed to get forecast for {city.name}. Status code: {response.status_code}")
                continue

            # Get the weather data from the response
            data = response.json()

            day_intervals = data['dayIntervals']
            for day in day_intervals[:8]:
                date = parse(day.get("start"))
                condition = day.get("twentyFourHourSymbol")
                temperature_data = day.get("temperature")
                air_temperature_max = temperature_data.get("max")
                air_temperature_min = temperature_data.get("min")

                wind_data = day.get("wind")
                wind_speed = wind_data.get("max")

                precipitation_data = day.get("precipitation")
                precipitation = precipitation_data.get("value")

                data_values = {
                    "date": date,
                    "condition": condition,
                    "parameters": {
                        "air_temperature_max": air_temperature_max,
                        "air_temperature_min": air_temperature_min,
                        "wind_speed": wind_speed,
                        "precipitation_amount": precipitation
                    }
                }

                condition = data_values.get('condition')

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
                for key, value in data_values.get("parameters", {}).items():
                    if parameters_dict.get(key) is None:
                        logger.warning(f"parameter: {key} not mapped set in Forecast Settings")
                        continue

                    parameter = parameters_dict[key]
                    data_value = DataValue(parameter=parameter, value=value)
                    city_forecast.data_values.add(data_value)

                if date in cities_data:
                    cities_data[date].append(city_forecast)
                else:
                    cities_data[date] = [city_forecast]

        for time, city_forecasts in cities_data.items():
            forecast = Forecast.objects.filter(forecast_date=time, effective_period=forecast_period)
            if forecast.exists():
                forecast.delete()

            forecast = Forecast(forecast_date=time, effective_period=forecast_period, source="yr")

            for city_forecast in city_forecasts:
                forecast.city_forecasts.add(city_forecast)

            forecast.save()
