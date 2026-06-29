"""
Shared dispatcher for automated forecast ingestion.

Resolves the active provider from a ForecastSetting and runs the matching
provider service. Used by both the ``generate_auto_forecast`` management command
and the admin "Pull forecasts now" button so they share one code path.
"""

import logging
from typing import Optional

from forecastmanager.providers import PROVIDER_OPEN_METEO, PROVIDER_YR
from forecastmanager.services.ingest import FORECAST_HOURS
from forecastmanager.services.open_meteo import OpenMeteoForecastService
from forecastmanager.services.types import IngestResult
from forecastmanager.services.yr import run_yr_forecast

logger = logging.getLogger(__name__)


#: Default forecast hours (Open-Meteo only) — standard 3-hourly slots.
DEFAULT_HOURS = list(FORECAST_HOURS)


class AutoForecastError(RuntimeError):
    """Raised when an automated forecast run cannot proceed."""


def run_auto_forecast(
    forecast_setting,
    city_filter: Optional[list[str]] = None,
    dry_run: bool = False,
    hours: Optional[list[int]] = None,
) -> IngestResult:
    """
    Run an automated forecast pull for the provider configured in settings.

    Args:
        forecast_setting: A ForecastSetting instance.
        city_filter: Restrict to these city names. Defaults to all cities.
        dry_run: When True, fetch but do not write to the database.
        hours: Hours of day to create periods for (Open-Meteo only).

    Returns:
        An IngestResult with ``saved``, ``skipped`` and ``errors``.

    Raises:
        AutoForecastError: If automation is disabled or the provider is unknown.
    """
    if not forecast_setting.enable_auto_forecast:
        raise AutoForecastError("Automated forecasts are disabled in settings.")

    provider = forecast_setting.forecast_provider
    field_map = forecast_setting.get_provider_field_map(provider)

    if provider == PROVIDER_OPEN_METEO:
        service = OpenMeteoForecastService(
            forecast_hours=hours or DEFAULT_HOURS,
            field_map=field_map or None,
        )
        try:
            return service.run(city_filter=city_filter, dry_run=dry_run)
        except (RuntimeError, ValueError) as exc:
            raise AutoForecastError(str(exc)) from exc

    if provider == PROVIDER_YR:
        try:
            return run_yr_forecast(
                field_map=field_map or None,
                city_filter=city_filter,
                dry_run=dry_run,
            )
        except (RuntimeError, ValueError) as exc:
            raise AutoForecastError(str(exc)) from exc

    raise AutoForecastError(f"Unknown provider: {provider}")
