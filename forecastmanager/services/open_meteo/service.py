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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, cast
from django.db.models import Manager
from django.utils import timezone
from wagtail.models import Site
from forecastmanager.forecast_settings import (
    ForecastDataParameters,
    ForecastSetting,
    WeatherCondition,
)
from forecastmanager.models import City, Forecast
from forecastmanager.services.ingest import (
    CityForecastRecord,
    commit_records,
    is_wanted_slot,
)
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

# Number of cities fetched in parallel. Open-Meteo is generous, but keep this
# modest to stay well within fair-use limits.
MAX_FETCH_WORKERS = 8


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
        self._status = Forecast.STATUS_DRAFT

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
        self._status = (
            Forecast.STATUS_PUBLISHED
            if getattr(forecast_setting, "auto_publish_forecasts", False)
            else Forecast.STATUS_DRAFT
        )
        parameters_dict = self._ensure_parameters(forecast_setting)
        cities = self._resolve_cities(city_filter)

        logger.info("Cities: %s", [c.name for c in cities])
        logger.info("Forecast hours: %s", self.forecast_hours)

        result = IngestResult()

        # Phase 1: fetch all cities concurrently (I/O-bound). The client does
        # only network work, so it is safe to call from worker threads.
        logger.info(
            "Fetching %d cities (up to %d in parallel)...",
            len(cities), MAX_FETCH_WORKERS,
        )
        fetched: list[tuple[City, Optional[dict]]] = []
        with ThreadPoolExecutor(max_workers=min(MAX_FETCH_WORKERS, len(cities))) as executor:
            future_to_city = {
                executor.submit(
                    self._client.fetch,
                    lat=city.y,
                    lon=city.x,
                    city_name=city.name or "",
                    hourly_vars=self._hourly_vars,
                ): city
                for city in cities
            }
            for future in as_completed(future_to_city):
                city = future_to_city[future]
                try:
                    data = future.result()
                except Exception as exc:  # network/parse failure for one city
                    logger.error("Fetch failed for %s: %s", city.name, exc)
                    data = None
                fetched.append((city, data))

        # Phase 2: parse responses into normalised records, keyed by
        # (date, hour, city) so duplicates collapse (main thread).
        records_by_key: dict[tuple, CityForecastRecord] = {}
        for city, data in fetched:
            self._collect_records(
                city, data, forecast_setting, parameters_dict, records_by_key, result
            )

        # Phase 3: bulk write everything in a handful of queries.
        commit_records(
            list(records_by_key.values()),
            source="open_meteo",
            status=self._status,
            forecast_setting=forecast_setting,
            result=result,
            dry_run=dry_run,
        )

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

    def _collect_records(
        self,
        city: City,
        data: Optional[dict],
        forecast_setting: ForecastSetting,
        parameters_dict: dict,
        records_by_key: dict,
        result: IngestResult,
    ) -> None:
        """
        Parse one city's response into normalised records.

        Records are written into ``records_by_key`` keyed by
        ``(date, hour, city_id)`` so duplicate timestamps collapse. No database
        writes happen here — :func:`commit_records` does the bulk write.

        Args:
            city: The City record being processed.
            data: Raw Open-Meteo response (or None if the fetch failed).
            forecast_setting: Active ForecastSetting instance.
            parameters_dict: Mapping of parameter key -> ForecastDataParameters.
            records_by_key: Accumulator dict updated in place.
            result: Mutable IngestResult updated in place.
        """
        logger.info("Processing city: %s", city.name)

        if data is None:
            result.skipped += 1
            result.errors.append(f"API request failed for {city.name or ''}")
            return

        # Pull every hour, then keep the current day hourly and later days
        # 3-hourly (self.forecast_hours is the sparse set for later days).
        today = timezone.localdate()
        entries = self._client.parse_hourly(
            data, target_hours=list(range(24)), hourly_vars=self._hourly_vars
        )
        if not entries:
            logger.warning("No hourly data returned")
            result.skipped += 1
            return

        for entry in entries:
            date = entry["date"]
            hour = entry["hour"]

            if not is_wanted_slot(date, hour, today, self.forecast_hours):
                continue

            wmo_code = entry.get("weathercode")

            if wmo_code is None:
                logger.warning("  No weathercode for %s %02d:00, skipping", date, hour)
                result.skipped += 1
                continue

            condition = self._get_or_create_condition(forecast_setting, int(wmo_code))

            values = {}
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
                values[param.id] = str(val)

            records_by_key[(date, hour, city.id)] = CityForecastRecord(
                date=date,
                hour=hour,
                city_id=city.id,
                condition_id=condition.id,
                values=values,
            )

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
