"""
Forecast ingestion service for Open-Meteo.
This module owns all interactions with Django and forecastmanager models.
The HTTP layer is delegated to OpenMeteoClient so this class can be
tested with a mocked client.

Usage:

    from climweb.services.open_meteo import OpenMeteoForecastService

    service = OpenMeteoForecastService()
    result = service.run(city_filter=["Nairobi"], dry_run=False)
    print(f"Saved {result.saved} periods, {result.skipped} skipped.")
"""

import logging
from datetime import date as DateType
from datetime import time
from typing import TYPE_CHECKING, Optional, cast
from django.db import transaction
from django.db.models import Manager
from wagtail.models import Site
from forecastmanager.forecast_settings import (
    ForecastDataParameters,
    ForecastPeriod,
    ForecastSetting,
    WeatherCondition,
)
from forecastmanager.models import City, CityForecast, DataValue, Forecast
from .client import OpenMeteoClient
from .constants import (
    DEFAULT_FORECAST_HOURS,
    DEFAULT_PARAMETERS,
    FIELD_MAP,
    OPEN_METEO_URL,
    UNKNOWN_CONDITION,
    WMO_CONDITION_MAP,
)
from .types import IngestResult

logger = logging.getLogger(__name__)

class OpenMeteoForecastService:
    """
    Fetches forecast data from Open-Meteo and saves it to forecastmanager.

    Delegates HTTP communication to ``OpenMeteoClient``. All database
    interactions go through forecastmanager's model layer — no direct SQL.

    Example::

        service = OpenMeteoForecastService(forecast_hours=[6, 18])
        result = service.run(city_filter=["Nairobi", "Lagos"])
        if result.errors:
            for error in result.errors:
                logger.error(error)
    """

    def __init__(
        self,
        forecast_hours: Optional[list[int]] = None,
        api_url: str = OPEN_METEO_URL,
        request_timeout: int = 15,
        field_map: Optional[dict[str, str]] = None,
    ) -> None:
        """
        Initialise the service.

        Args:
            forecast_hours: Hours of day to create ForecastPeriods for.
                Defaults to DEFAULT_FORECAST_HOURS (6, 12, 18).
            api_url: Open-Meteo base URL. Override in tests or to point at a
                self-hosted instance.
            request_timeout: HTTP request timeout in seconds.
            field_map: Optional admin-configured mapping of Open-Meteo source
                field -> ForecastDataParameter key. When provided, it overrides
                the built-in FIELD_MAP and the service assumes the referenced
                parameters already exist (no defaults are auto-created).
        """
        self.forecast_hours = forecast_hours or DEFAULT_FORECAST_HOURS
        self._custom_field_map = bool(field_map)
        self.field_map = field_map or FIELD_MAP
        # Always include weathercode so weather conditions can be resolved.
        self._hourly_vars = list(dict.fromkeys(list(self.field_map.keys()) + ["weathercode"]))
        self._client = OpenMeteoClient(api_url=api_url, timeout=request_timeout)
        self._conditions_cache: dict[int, WeatherCondition] = {}

    def run(
        self,
        city_filter: Optional[list[str]] = None,
        dry_run: bool = False,
    ) -> IngestResult:
        """
        Fetch and ingest forecasts for all (or filtered) cities.

        Args:
            city_filter: Optional list of city names to process. When None,
                all cities in the database are processed.
            dry_run: When True, log what would be saved without writing to
                the database.

        Returns:
            An IngestResult summarising how many periods were saved or skipped.

        Raises:
            RuntimeError: If no default Wagtail site or ForecastSetting exists.
            ValueError: If any names in city_filter don't match City records.
        """
        logger.info("=" * 60)
        logger.info("Open-Meteo -> ClimWeb Forecast Service")
        logger.info("Mode: %s", "DRY RUN" if dry_run else "LIVE")
        logger.info("=" * 60)

        forecast_setting = self._get_forecast_setting()
        parameters_dict = self._ensure_parameters(forecast_setting)
        cities = self._resolve_cities(city_filter)

        logger.info("Cities: %s", [c.name for c in cities])
        logger.info("Forecast hours: %s", self.forecast_hours)

        result = IngestResult()
        for city in cities:
            self._ingest_city(city, forecast_setting, parameters_dict, dry_run, result)

        logger.info("=" * 60)
        logger.info(
            "Done. %s %d forecast period(s). %d skipped.",
            "Would have saved" if dry_run else "Saved",
            result.saved,
            result.skipped,
        )
        logger.info("=" * 60)
        return result

    def _get_forecast_setting(self) -> ForecastSetting:
        """
        Return the ForecastSetting for the default Wagtail site.

        Raises:
            RuntimeError: If no default site or ForecastSetting is found.
        """
        try:
            site = Site.objects.get(is_default_site=True)
        except Site.DoesNotExist as exc:
            raise RuntimeError(
                "No default Wagtail site found. "
                "Run migrations and create a site first."
            ) from exc

        setting = ForecastSetting.for_site(site)
        if not setting:
            raise RuntimeError(
                "No ForecastSetting found. "
                "Configure it in the Wagtail admin first."
            )
        return setting

    def _ensure_parameters(self, forecast_setting: ForecastSetting) -> dict:
        """
        Ensure all required ForecastDataParameters exist, creating missing ones.

        Args:
            forecast_setting: The active ForecastSetting instance.

        Returns:
            Dict mapping parameter key strings to ForecastDataParameters instances.
        """
        # data_parameters is a reverse relation (ParentalKey), so Pylance knows it's a Manager and can call .all() on it.
        data_parameters = cast(Manager, forecast_setting.data_parameters)
        existing = {p.parameter: p for p in data_parameters.all()}

        # When an admin-configured field map drives the run, the mapping
        # references parameters the admin already created — don't auto-create
        # the built-in defaults.
        if self._custom_field_map:
            return existing

        for param_def in DEFAULT_PARAMETERS:
            key = param_def["parameter"]
            if key not in existing:
                new_param = ForecastDataParameters.objects.create(
                    parent=forecast_setting,
                    use_known_parameters=False,
                    **param_def,
                )
                existing[key] = new_param
                logger.info("Created ForecastDataParameter: %s", key)
        return existing

    def _resolve_cities(self, city_filter: Optional[list[str]]) -> list[City]:
        """
        Return the list of City records to process.

        Args:
            city_filter: Optional list of city names. When None, all cities
                are returned.

        Raises:
            ValueError: If any requested city names are not found.
            RuntimeError: If no cities exist in the database at all.
        """
        cities = City.objects.all()

        if city_filter:
            cities = cities.filter(name__in=city_filter)
            found = set(cities.values_list("name", flat=True))
            missing = set(city_filter) - found
            if missing:
                raise ValueError(
                    f"Cities not found in ClimWeb: {missing}. "
                    "Add them via City Forecast -> Cities in the admin."
                )

        if not cities.exists():
            raise RuntimeError(
                "No cities found. "
                "Add at least one city in the ClimWeb admin."
            )

        return list(cities)

    def _ingest_city(
        self,
        city: City,
        forecast_setting: ForecastSetting,
        parameters_dict: dict,
        dry_run: bool,
        result: IngestResult,
    ) -> None:
        """
        Fetch and ingest forecast data for a single city.

        Args:
            city: The City record to process.
            forecast_setting: Active ForecastSetting instance.
            parameters_dict: Mapping of parameter key -> ForecastDataParameters.
            dry_run: When True, log without writing to the database.
            result: Mutable IngestResult updated in place.
        """
        logger.info("Processing city: %s", city.name)

        # city.name is nullable in the model, fall back to empty string for the log message so we don't pass str | None to client.fetch().
        city_name: str = city.name or ""

        data = self._client.fetch(
            lat=city.y, lon=city.x, city_name=city_name, hourly_vars=self._hourly_vars
        )
        if data is None:
            result.skipped += 1
            result.errors.append(f"API request failed for {city_name}")
            return

        entries = self._client.parse_hourly(
            data, target_hours=self.forecast_hours, hourly_vars=self._hourly_vars
        )
        if not entries:
            logger.warning("No hourly data for target hours %s", self.forecast_hours)
            result.skipped += 1
            return

        for entry in entries:
            self._save_entry(
                entry, city, forecast_setting, parameters_dict, dry_run, result
            )

    def _save_entry(
        self,
        entry: dict,
        city: City,
        forecast_setting: ForecastSetting,
        parameters_dict: dict,
        dry_run: bool,
        result: IngestResult,
    ) -> None:
        """
        Persist (or dry-run log) a single hourly forecast entry.

        Args:
            entry: Parsed hourly dict from ``OpenMeteoClient.parse_hourly``.
            city: City this entry belongs to.
            forecast_setting: Active ForecastSetting instance.
            parameters_dict: Mapping of parameter key -> ForecastDataParameters.
            dry_run: When True, log without writing.
            result: Mutable IngestResult updated in place.
        """
        date = entry["date"]
        hour = entry["hour"]
        wmo_code = entry.get("weathercode")

        if wmo_code is None:
            logger.warning("  No weathercode for %s %02d:00, skipping", date, hour)
            result.skipped += 1
            return

        condition = self._get_or_create_condition(forecast_setting, int(wmo_code))
        period = self._get_or_create_period(forecast_setting, hour)

        if dry_run:
            logger.info(
                "  [DRY RUN] Would save: %s %02d:00 | %s | %s",
                date, hour, city.name, condition.label,
            )
            for om_key, internal_key in self.field_map.items():
                val = entry.get(om_key)
                if val is not None and internal_key in parameters_dict:
                    logger.info("    %s = %s", internal_key, val)
            result.saved += 1
            return

        with transaction.atomic():
            forecast_obj = self._get_or_replace_forecast(date, period, city)

            city_forecast = CityForecast(city=city, condition=condition)

            # data_values is a reverse relation, so Pylance knows it's a Manager with an .add() method.
            data_values_mgr = cast(Manager, city_forecast.data_values)

            for om_key, internal_key in self.field_map.items():
                val = entry.get(om_key)
                if val is None:
                    continue
                param = parameters_dict.get(internal_key)
                if param is None:
                    logger.warning(
                        "  Parameter '%s' not in settings, skipping", internal_key
                    )
                    continue
                data_values_mgr.add(DataValue(parameter=param, value=str(val)))

            # city_forecasts is a reverse relation, so Pylance knows it's a Manager with an .add() method.
            city_forecasts_mgr = cast(Manager, forecast_obj.city_forecasts)
            city_forecasts_mgr.add(city_forecast)
            forecast_obj.save()

        result.saved += 1
        logger.info(
            "  Saved %s %02d:00 | %s | %s", date, hour, city.name, condition.label
        )

    def _get_or_replace_forecast(
        self, date: DateType, period: ForecastPeriod, city: City
    ) -> Forecast:
        """
        Return an existing Forecast for date + period, replacing city data.

        If a Forecast already exists, the CityForecast for this city is
        deleted and the parent Forecast reused (preserving other cities).
        If none exists, a new unsaved Forecast instance is returned.

        Args:
            date: The forecast date.
            period: The ForecastPeriod for this time slot.
            city: The city whose data is being replaced.

        Returns:
            A Forecast instance (existing or new, not yet saved).
        """
        existing_qs = Forecast.objects.filter(
            forecast_date=date, effective_period=period
        )
        if existing_qs.exists():
            forecast_obj = existing_qs.first()
            # first() returns Forecast | None; existence is guaranteed by the .exists() check above, so assert to narrow the type for Pylance.
            assert forecast_obj is not None

            city_forecasts_mgr = cast(Manager, forecast_obj.city_forecasts)
            city_qs = city_forecasts_mgr.filter(city=city)
            if city_qs.exists():
                city_qs.delete()
                logger.info(
                    "  Replaced existing CityForecast for %s %s", city.name, date
                )
            return forecast_obj

        return Forecast(forecast_date=date, effective_period=period, source="local")

    def _get_or_create_period(
        self, forecast_setting: ForecastSetting, hour: int
    ) -> ForecastPeriod:
        """
        Return (or create) a ForecastPeriod for the given hour.

        Args:
            forecast_setting: Parent ForecastSetting instance.
            hour: Hour of day (0-23).

        Returns:
            A ForecastPeriod instance.
        """
        effective_time = time(hour, 0)
        period = ForecastPeriod.objects.filter(
            parent=forecast_setting,
            forecast_effective_time=effective_time,
        ).first()
        if period is None:
            label = f"{hour:02d}:00"
            period = ForecastPeriod.objects.create(
                parent=forecast_setting,
                forecast_effective_time=effective_time,
                label=label,
            )
            logger.info("  Created ForecastPeriod: %s", label)
        return period

    def _get_or_create_condition(
        self, forecast_setting: ForecastSetting, wmo_code: int
    ) -> WeatherCondition:
        """
        Map a WMO weather code to a WeatherCondition, creating it if needed.

        Results are cached in ``self._conditions_cache`` for the lifetime of
        the service instance to avoid redundant database lookups.

        Args:
            forecast_setting: Parent ForecastSetting instance.
            wmo_code: Integer WMO weather code from Open-Meteo.

        Returns:
            A WeatherCondition instance.
        """
        if wmo_code in self._conditions_cache:
            return self._conditions_cache[wmo_code]

        symbol, label = WMO_CONDITION_MAP.get(wmo_code, UNKNOWN_CONDITION)
        if wmo_code not in WMO_CONDITION_MAP:
            logger.warning("Unknown WMO code %d, using fallback condition", wmo_code)

        condition = (
            WeatherCondition.objects.filter(
                parent=forecast_setting, symbol=symbol
            ).first()
            or WeatherCondition.objects.filter(
                parent=forecast_setting, label=label
            ).first()
        )

        if condition is None:
            condition = WeatherCondition.objects.create(
                parent=forecast_setting, symbol=symbol, label=label
            )
            logger.info("  Created WeatherCondition: %s (%s)", label, symbol)

        self._conditions_cache[wmo_code] = condition
        return condition
