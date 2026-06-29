"""
Shared bulk ingestion for forecast provider services (yr.no, Open-Meteo).

Provider services parse their API responses into a list of normalised
``CityForecastRecord`` objects, then call :func:`commit_records`, which writes
them to the database using *set-based* operations instead of row-by-row ORM
calls:

  * one query to load the existing CityForecasts for the affected forecasts,
  * one bulk delete of the auto-generated rows being replaced,
  * one ``bulk_create`` for the new CityForecasts, and
  * one ``bulk_create`` for their DataValues.

Forecaster-authored (``MANUAL``) city forecasts are never touched. This keeps a
full pull to a handful of queries rather than tens of thousands.
"""

import logging
from dataclasses import dataclass
from datetime import date as DateType
from datetime import time
from typing import Optional

from django.db import transaction

from forecastmanager.forecast_settings import ForecastPeriod
from forecastmanager.models import CityForecast, DataValue, Forecast

logger = logging.getLogger(__name__)

#: Sparse (3-hourly) forecast periods kept for days after the current one.
FORECAST_HOURS = [0, 3, 6, 9, 12, 15, 18, 21]


def is_wanted_slot(forecast_date, hour, today, sparse_hours=FORECAST_HOURS) -> bool:
    """
    Decide whether a forecast time slot should be stored.

    The current day is kept at full hourly resolution; later days are thinned to
    the sparse (3-hourly) periods.

    Args:
        forecast_date: The slot's local date.
        hour: The slot's hour of day (0-23).
        today: The current local date.
        sparse_hours: Hours to keep on days after today.
    """
    if forecast_date == today:
        return True
    return hour in sparse_hours


@dataclass
class CityForecastRecord:
    """One city's forecast for a single date + hour slot."""

    date: DateType
    hour: int
    city_id: object
    condition_id: int
    values: dict  # parameter_id -> value (str)


def commit_records(
    records: list[CityForecastRecord],
    source: str,
    status: str,
    forecast_setting,
    result,
    dry_run: bool = False,
) -> list:
    """
    Persist normalised forecast records in bulk.

    Args:
        records: Parsed records to write. Duplicates on (date, hour, city) must
            already be resolved by the caller.
        source: Forecast.source value to stamp on newly created forecasts.
        status: Forecast.status for newly created forecasts (published/draft).
        forecast_setting: Active ForecastSetting (owns periods).
        result: Mutable IngestResult; ``saved`` / ``skipped`` are updated.
        dry_run: When True, nothing is written.

    Returns:
        List of affected Forecast primary keys (empty on dry run / no records).
    """
    if not records:
        return []

    if dry_run:
        result.saved += len(records)
        return []

    with transaction.atomic():
        # Resolve (and create once) the ForecastPeriod for each distinct hour.
        periods: dict[int, ForecastPeriod] = {}
        for hour in sorted({r.hour for r in records}):
            period, _ = ForecastPeriod.objects.get_or_create(
                parent=forecast_setting,
                forecast_effective_time=time(hour, 0),
                defaults={"label": f"{hour:02d}:00"},
            )
            periods[hour] = period

        # Resolve (or create) the parent Forecast for each distinct (date, hour).
        # An existing Forecast is reused so a forecaster's publish status and
        # other cities' data are preserved.
        forecast_by_key: dict[tuple, Forecast] = {}
        for key in {(r.date, r.hour) for r in records}:
            date, hour = key
            forecast, _ = Forecast.objects.get_or_create(
                forecast_date=date,
                effective_period=periods[hour],
                defaults={"source": source, "status": status},
            )
            forecast_by_key[key] = forecast

        # One query for all existing city forecasts in the affected forecasts.
        forecast_ids = [f.id for f in forecast_by_key.values()]
        existing = {
            (cf.parent_id, cf.city_id): cf
            for cf in CityForecast.objects.filter(parent_id__in=forecast_ids).only(
                "id", "parent_id", "city_id", "data_source"
            )
        }

        to_delete_ids = []
        new_cfs = []
        new_cf_records = []  # parallel to new_cfs, for building DataValues
        for record in records:
            forecast = forecast_by_key[(record.date, record.hour)]
            existing_cf = existing.get((forecast.id, record.city_id))
            if existing_cf is not None:
                if existing_cf.data_source == CityForecast.DATA_SOURCE_MANUAL:
                    # Forecaster-authored: protected, leave untouched.
                    result.skipped += 1
                    continue
                to_delete_ids.append(existing_cf.id)
            new_cfs.append(
                CityForecast(
                    parent_id=forecast.id,
                    city_id=record.city_id,
                    condition_id=record.condition_id,
                    data_source=CityForecast.DATA_SOURCE_AUTO,
                )
            )
            new_cf_records.append(record)

        # Replace auto rows in one delete (DataValues cascade), then bulk insert.
        if to_delete_ids:
            CityForecast.objects.filter(id__in=to_delete_ids).delete()

        created = CityForecast.objects.bulk_create(new_cfs)

        data_values = []
        for city_forecast, record in zip(created, new_cf_records):
            for parameter_id, value in record.values.items():
                data_values.append(
                    DataValue(
                        parent_id=city_forecast.id,
                        parameter_id=parameter_id,
                        value=value,
                    )
                )
        if data_values:
            DataValue.objects.bulk_create(data_values)

        result.saved += len(created)

    return forecast_ids
