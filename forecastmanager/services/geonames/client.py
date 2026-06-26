"""
HTTP client for the GeoNames search web service.

This module is free of Django imports so it can be unit-tested without a
database. It handles network communication and parsing the raw API response
into plain dicts.
"""

import logging
from typing import Optional

import requests

from .constants import GEONAMES_SEARCH_URL, GEONAMES_MAX_ROWS

logger = logging.getLogger(__name__)


class GeoNamesError(RuntimeError):
    """Raised when the GeoNames service returns an error or is unreachable."""


class GeoNamesClient:
    """Thin HTTP wrapper around the GeoNames ``searchJSON`` endpoint.

    Example::
        client = GeoNamesClient(username="demo")
        places = client.search(
            country="MW",
            feature_class="P",
            feature_codes=["PPLC", "PPLA"],
            order_by="population",
            max_rows=200,
        )
    """

    def __init__(
        self,
        username: str,
        api_url: str = GEONAMES_SEARCH_URL,
        timeout: int = 30,
    ) -> None:
        if not username:
            raise GeoNamesError(
                "A GeoNames username is required. Set it under "
                "Forecast Settings > Other Settings > GeoNames username."
            )
        self.username = username
        self.api_url = api_url
        self.timeout = timeout

    def search(
        self,
        country: str,
        feature_class: Optional[str] = None,
        feature_codes: Optional[list[str]] = None,
        order_by: str = "population",
        max_rows: int = GEONAMES_MAX_ROWS,
    ) -> list[dict]:
        """
        Query GeoNames for places in a country.

        Args:
            country: ISO-3166 alpha-2 country code (e.g. "MW").
            feature_class: Restrict to a feature class, e.g. "P".
            feature_codes: Restrict to specific feature codes (repeatable),
                e.g. ["PPLC", "PPLA", "PPLA2"].
            order_by: GeoNames ordering ("population", "relevance", ...).
            max_rows: Number of rows to request (GeoNames caps this at 1000).

        Returns:
            List of raw GeoNames record dicts.

        Raises:
            GeoNamesError: On network failure or an API-level error response.
        """
        params = {
            "country": country.upper(),
            "orderby": order_by,
            "maxRows": min(max_rows, GEONAMES_MAX_ROWS),
            "username": self.username,
            "style": "MEDIUM",
        }
        if feature_class:
            params["featureClass"] = feature_class
        if feature_codes:
            # requests serialises a list value into repeated query params.
            params["featureCode"] = feature_codes

        try:
            response = requests.get(self.api_url, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            raise GeoNamesError(f"Could not reach GeoNames: {exc}") from exc

        # GeoNames reports auth/quota problems inside the response body (sometimes
        # with a non-2xx status). Try to surface that message before raising on
        # the HTTP status, since it is far more actionable than a bare code.
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict) and "status" in payload:
            message = payload["status"].get("message", "Unknown GeoNames error.")
            raise GeoNamesError(f"GeoNames error: {message.strip()}")

        if response.status_code == 401:
            raise GeoNamesError(
                "GeoNames rejected the request (401). The account's free web "
                "services are most likely not enabled yet — log in at "
                "geonames.org, open your account page, and click "
                "\"Click here to enable\" under Free Web Services."
            )

        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise GeoNamesError(f"Could not reach GeoNames: {exc}") from exc

        if payload is None:
            raise GeoNamesError("GeoNames returned a non-JSON response.")

        return payload.get("geonames", [])
