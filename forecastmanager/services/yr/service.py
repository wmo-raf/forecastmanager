"""
Forecast ingestion service for yr.no (Met Norway locationforecast API).

Extracted from the original ``generate_forecast`` management command so the
logic can be reused by the unified ``generate_auto_forecast`` dispatcher and
honour an admin-configured field map. With no field map supplied it reproduces
the historical behaviour, where provider field names map onto identically named
ForecastDataParameters.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import requests
from dateutil.parser import parse
from django.utils import timezone
from wagtail import hooks
from wagtail.models import Site

from forecastmanager.constants import WEATHER_CONDITIONS_AS_DICT
from forecastmanager.forecast_settings import (
    ForecastSetting,
    WeatherCondition,
    ForecastDataParameters,
)
from forecastmanager.models import City, Forecast
from forecastmanager.services.ingest import (
    CityForecastRecord,
    commit_records,
    is_wanted_slot,
)
from forecastmanager.services.types import IngestResult

logger = logging.getLogger(__name__)

# Met Norway locationforecast API.
BASE_URL = "https://api.met.no/weatherapi/locationforecast/2.0/complete"

# Per-request timeout (seconds) so a slow/hung response can't stall the whole run.
REQUEST_TIMEOUT = 30

# Number of cities fetched in parallel. Kept modest to respect met.no rate limits.
MAX_FETCH_WORKERS = 8

DEFAULT_INSTANT_DATA_PARAMETERS = [
    {"parameter": "air_pressure_at_sea_level", "name": "Air Pressure (Sea level)", "parameter_unit": "hPa"},
    {"parameter": "air_temperature", "name": "Air Temperature", "parameter_unit": "°C"},
    {"parameter": "wind_speed", "name": "Wind Speed", "parameter_unit": "m/s"},
    {"parameter": "wind_from_direction", "name": "Wind Direction", "parameter_unit": "degrees"},
]

DEFAULT_NEXT_HOURS_DATA_PARAMETERS = [
    {"parameter": "air_temperature_min", "name": "Minimum Air Temperature", "parameter_unit": "°C"},
    {"parameter": "air_temperature_max", "name": "Maximum Air Temperature", "parameter_unit": "°C"},
    {"parameter": "precipitation_amount", "name": "Precipitation Amount", "parameter_unit": "mm"},
]

DEFAULT_PARAMETERS = DEFAULT_INSTANT_DATA_PARAMETERS + DEFAULT_NEXT_HOURS_DATA_PARAMETERS


def _flatten_entry_values(data_values: dict) -> dict:
    """
    Collapse a yr timeseries entry into a flat ``{field: value}`` dict.

    instant details are combined with the next_1_hours / next_6_hours details.
    next_1_hours takes precedence over next_6_hours for overlapping keys.
    """
    flat = {}
    instant = data_values.get("instant", {}).get("details", {})
    flat.update(instant)

    next_6 = data_values.get("next_6_hours", {}).get("details", {})
    flat.update(next_6)

    next_1 = data_values.get("next_1_hours", {}).get("details", {})
    flat.update(next_1)

    return flat


def _fetch_city(city, user_agent: str):
    """
    Fetch the yr.no forecast for one city. Network only — no ORM access, so it
    is safe to call from worker threads.

    Returns a ``(city, data, error)`` tuple where exactly one of ``data`` /
    ``error`` is set.
    """
    url = f"{BASE_URL}?lat={city.y}&lon={city.x}"
    try:
        response = requests.get(
            url, headers={"User-Agent": user_agent}, timeout=REQUEST_TIMEOUT
        )
    except requests.RequestException as exc:
        return city, None, f"Failed to get forecast for {city.name}: {exc}"

    if response.status_code >= 400:
        return city, None, (
            f"Failed to get forecast for {city.name}. Status code: {response.status_code}"
        )

    try:
        return city, response.json(), None
    except ValueError as exc:
        return city, None, f"Invalid JSON for {city.name}: {exc}"


def run_yr_forecast(
    field_map: Optional[dict] = None,
    city_filter: Optional[list] = None,
    dry_run: bool = False,
) -> IngestResult:
    """
    Fetch 7-day forecasts from yr.no for all (or filtered) cities and save them.

    Args:
        field_map: Optional mapping of ``{yr_source_field: parameter_key}``.
            When omitted, an identity map over the configured parameters is
            used (the historical behaviour).
        city_filter: Optional list of city names to restrict to.
        dry_run: When True, log what would be saved without writing.

    Returns:
        An IngestResult summarising saved/skipped counts and any errors.
    """
    result = IngestResult()

    cities = City.objects.all()
    if city_filter:
        cities = cities.filter(name__in=city_filter)
    if not cities:
        result.errors.append("No cities found")
        logger.error("No cities found")
        return result

    site = Site.objects.get(is_default_site=True)
    if not site:
        result.errors.append("No default site found")
        logger.error("No default site found")
        return result

    forecast_setting = ForecastSetting.for_site(site)

    site_name = site.site_name
    root_url = site.root_url
    user_agent = f"ClimWeb {root_url}"
    if site_name:
        user_agent = f"{site_name}/{user_agent}"
    user_agent = user_agent.strip()

    if not forecast_setting.enable_auto_forecast:
        result.errors.append("Auto forecast is disabled")
        logger.error("Auto forecast is disabled")
        return result

    conditions = forecast_setting.weather_conditions.all()
    conditions_by_symbol = {condition.symbol: condition for condition in conditions}

    parameters = forecast_setting.data_parameters.all()
    if not parameters.exists():
        for default_parameter in DEFAULT_PARAMETERS:
            ForecastDataParameters.objects.create(parent=forecast_setting, **default_parameter)
        parameters = forecast_setting.data_parameters.all()

    parameters_dict = {parameter.parameter: parameter for parameter in parameters}

    status = (
        Forecast.STATUS_PUBLISHED
        if getattr(forecast_setting, "auto_publish_forecasts", False)
        else Forecast.STATUS_DRAFT
    )

    # With no admin mapping, fall back to an identity map (field name == param key),
    # which reproduces the original command behaviour.
    effective_map = field_map or {key: key for key in parameters_dict.keys()}

    # Phase 1: fetch every city's forecast concurrently (I/O-bound network work).
    # Materialise the queryset first so worker threads don't touch the ORM.
    cities_list = list(cities)
    logger.info("Fetching forecasts for %d cities (up to %d in parallel)...",
                len(cities_list), MAX_FETCH_WORKERS)

    fetched = []
    with ThreadPoolExecutor(max_workers=min(MAX_FETCH_WORKERS, len(cities_list))) as executor:
        for city, data, error in executor.map(lambda c: _fetch_city(c, user_agent), cities_list):
            if error:
                logger.error(error)
                result.errors.append(error)
                result.skipped += 1
                continue
            fetched.append((city, data))

    # Phase 2: parse each response into normalised records, keyed by
    # (date, hour, city) so duplicate timestamps collapse. Only the 3-hourly
    # forecast periods are kept. WeatherCondition lookups/creates happen here
    # (main thread).
    first_datetime = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    today = first_datetime.date()
    max_days = 6
    last_datetime = (first_datetime + timezone.timedelta(days=max_days)).replace(
        hour=23, minute=59, second=59
    )

    records_by_key: dict[tuple, CityForecastRecord] = {}

    for city, data in fetched:
        timeseries = data.get('properties', {}).get('timeseries')
        if not timeseries:
            continue

        for time_data in timeseries:
            utc_date = parse(time_data.get("time"))
            timezone_date = timezone.localtime(utc_date)

            if timezone_date < first_datetime or timezone_date > last_datetime:
                continue

            # Hourly for the current day, 3-hourly for later days.
            if not is_wanted_slot(timezone_date.date(), timezone_date.hour, today):
                continue

            data_values = time_data.get("data", {})

            condition = data_values.get("next_1_hours", {}).get("summary", {}).get("symbol_code")
            if condition is None:
                condition = data_values.get("next_6_hours", {}).get("summary", {}).get("symbol_code")

            if conditions_by_symbol.get(condition) is None:
                condition_info = WEATHER_CONDITIONS_AS_DICT.get(condition)
                if condition_info is None:
                    continue
                label = condition_info.get('name')
                created_condition = WeatherCondition.objects.create(
                    parent=forecast_setting, symbol=condition, label=label
                )
                conditions_by_symbol[created_condition.symbol] = created_condition

            condition_obj = conditions_by_symbol.get(condition)
            if condition_obj is None:
                logger.warning(f"Cannot find or create condition for symbol code: {condition}")
                continue

            flat_values = _flatten_entry_values(data_values)
            values = {}
            for source_field, param_key in effective_map.items():
                if param_key not in parameters_dict:
                    continue
                if source_field not in flat_values:
                    continue
                values[parameters_dict[param_key].id] = str(flat_values[source_field])

            records_by_key[(timezone_date.date(), timezone_date.hour, city.id)] = CityForecastRecord(
                date=timezone_date.date(),
                hour=timezone_date.hour,
                city_id=city.id,
                condition_id=condition_obj.id,
                values=values,
            )

    # Phase 3: bulk write.
    created_forecast_pks = commit_records(
        list(records_by_key.values()),
        source="yr",
        status=status,
        forecast_setting=forecast_setting,
        result=result,
        dry_run=dry_run,
    )

    if not dry_run:
        for fn in hooks.get_hooks("after_generate_forecast"):
            fn(created_forecast_pks)

    return result
