"""
HTTP client for the Open-Meteo forecast API.
This module is free of Django model imports so it can be
unit-tested without a database. It handles network communication
and parsing the raw API response into a list of flat hourly dicts.
"""

import logging
from datetime import datetime
from typing import Optional
import requests
from .constants import HOURLY_VARS, OPEN_METEO_URL

logger = logging.getLogger(__name__)

class OpenMeteoClient:
    """Thin HTTP wrapper around the Open-Meteo forecast API.

    Example::
        client = OpenMeteoClient()
        data = client.fetch(lat=-1.286, lon=36.817)
        entries = client.parse_hourly(data, target_hours=[6, 12, 18])
    """

    def __init__(
        self,
        api_url: str = OPEN_METEO_URL,
        timeout: int = 15,
    ) -> None:
        """
        Initialise the client.

        Args:
            api_url: Open-Meteo base URL. Override in tests or to point at a
                self-hosted instance.
            timeout: HTTP request timeout in seconds.
        """
        self.api_url = api_url
        self.timeout = timeout

    def fetch(self, lat: float, lon: float, city_name: str = "") -> Optional[dict]:
        """
        Fetch a 7-day hourly forecast for the given coordinates.

        Args:
            lat: Latitude of the location.
            lon: Longitude of the location.
            city_name: Used only for log messages.

        Returns:
            Parsed JSON response dict, or None if the request fails.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(HOURLY_VARS),
            "forecast_days": 7,
            "timezone": "auto",
        }
        logger.info(
            "  Fetching Open-Meteo for %s (lat=%s, lon=%s)",
            city_name or "unknown",
            lat,
            lon,
        )
        try:
            response = requests.get(self.api_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error(
                "  API request failed for %s: %s", city_name or "unknown", exc
            )
            return None

    def parse_hourly(self, data: dict, target_hours: list[int]) -> list[dict]:
        """
        Extract hourly entries for the specified target hours only.
        
        Args:
            data: Raw JSON response from Open-Meteo.
            target_hours: Hours of day (0-23) to include. All other hours
                are discarded.
                
        Returns:
            List of dicts, one per matching (date, hour) slot. Each dict
            contains ``date``, ``hour``, ``datetime``, and one key per
            variable in HOURLY_VARS with its value at that time index.
        """
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        results = []

        for i, time_str in enumerate(times):
            dt = datetime.fromisoformat(time_str)
            if dt.hour not in target_hours:
                continue

            entry: dict = {
                "datetime": dt,
                "date": dt.date(),
                "hour": dt.hour,
            }
            for var in HOURLY_VARS:
                values = hourly.get(var, [])
                entry[var] = values[i] if i < len(values) else None

            results.append(entry)

        return results