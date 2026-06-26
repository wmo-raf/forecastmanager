"""
GeoNames city-import orchestration.

The selection/parsing logic (``parse_place``, ``select_places``) is pure Python
with no Django imports, so it can be unit-tested without a database. Only
``GeoNamesImportService.import_to_db`` touches the ORM, and it imports the
model lazily.

Selection strategy (admin seats + fill by population):
    1. Always include administrative seats (PPLC, PPLA, PPLA2), ordered by
       administrative rank then population, so every regional and district
       capital is covered even when small.
    2. Fill the remaining slots, up to ``max_cities``, with the highest-
       population populated places not already chosen.
This guarantees administrative coverage *and* the population cap.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from .client import GeoNamesClient
from .constants import (
    ADMIN_SEAT_CODES,
    DEFAULT_MAX_CITIES,
    FEATURE_CLASS_POPULATED,
    FEATURE_CODE_PRIORITY,
    GEONAMES_MAX_ROWS,
    PPL,
)

logger = logging.getLogger(__name__)


@dataclass
class GeoNamesPlace:
    """A populated place returned by GeoNames."""

    geoname_id: int
    name: str
    lat: float
    lon: float
    feature_code: str
    population: int = 0
    admin_name: str = ""


@dataclass
class ImportResult:
    """Outcome of writing selected places to the City table."""

    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def parse_place(raw: dict) -> Optional[GeoNamesPlace]:
    """Convert a raw GeoNames record into a :class:`GeoNamesPlace`.

    Returns ``None`` for records missing the fields we need.
    """
    try:
        return GeoNamesPlace(
            geoname_id=int(raw["geonameId"]),
            name=raw["name"],
            lat=float(raw["lat"]),
            lon=float(raw["lng"]),
            feature_code=raw.get("fcode", PPL) or PPL,
            population=int(raw.get("population") or 0),
            admin_name=raw.get("adminName1", "") or "",
        )
    except (KeyError, TypeError, ValueError):
        logger.warning("Skipping malformed GeoNames record: %s", raw)
        return None


def select_places(
    admin_seats: list[GeoNamesPlace],
    populated: list[GeoNamesPlace],
    max_cities: int,
) -> list[GeoNamesPlace]:
    """Merge admin seats and populated places into a capped, de-duplicated list.

    Admin seats come first (by rank then population); remaining slots are filled
    with the most populous places. De-duplication is by GeoNames id.
    """
    admin_sorted = sorted(
        admin_seats,
        key=lambda p: (FEATURE_CODE_PRIORITY.get(p.feature_code, 99), -p.population),
    )
    populated_sorted = sorted(populated, key=lambda p: -p.population)

    selected: list[GeoNamesPlace] = []
    seen: set[int] = set()
    for place in [*admin_sorted, *populated_sorted]:
        if place.geoname_id in seen:
            continue
        seen.add(place.geoname_id)
        selected.append(place)
        if len(selected) >= max_cities:
            break

    return selected


class GeoNamesImportService:
    """Fetch, select, and persist cities from GeoNames."""

    def __init__(
        self,
        client: GeoNamesClient,
        max_cities: int = DEFAULT_MAX_CITIES,
    ) -> None:
        self.client = client
        self.max_cities = max(1, int(max_cities))

    def fetch_candidates(self, country: str) -> list[GeoNamesPlace]:
        """Fetch and select the cities to import for a country."""
        # Administrative seats — capitals and district centres, regardless of size.
        admin_raw = self.client.search(
            country=country,
            feature_codes=ADMIN_SEAT_CODES,
            order_by="population",
            max_rows=GEONAMES_MAX_ROWS,
        )
        # Most-populous populated places to fill remaining slots.
        populated_raw = self.client.search(
            country=country,
            feature_class=FEATURE_CLASS_POPULATED,
            order_by="population",
            max_rows=min(GEONAMES_MAX_ROWS, self.max_cities * 2),
        )

        admin_seats = [p for p in (parse_place(r) for r in admin_raw) if p]
        populated = [p for p in (parse_place(r) for r in populated_raw) if p]

        return select_places(admin_seats, populated, self.max_cities)

    def import_to_db(
        self,
        places: list[GeoNamesPlace],
        overwrite: bool = False,
    ) -> ImportResult:
        """Write selected places to the City table.

        City names are unique. An existing city is updated (location) only when
        ``overwrite`` is set, otherwise it is skipped. Duplicate names within the
        same batch are skipped after the first.
        """
        from django.contrib.gis.geos import Point
        from forecastmanager.models import City

        result = ImportResult()
        seen_names: set[str] = set()

        for place in places:
            key = place.name.casefold()
            if key in seen_names:
                result.skipped += 1
                continue
            seen_names.add(key)

            point = Point(x=place.lon, y=place.lat, srid=4326)
            existing = City.objects.filter(name__iexact=place.name).first()

            if existing:
                if not overwrite:
                    result.skipped += 1
                    continue
                existing.location = point
                existing.save()
                result.updated += 1
            else:
                City.objects.create(name=place.name, location=point)
                result.created += 1

        return result

    def run(
        self,
        country: str,
        overwrite: bool = False,
        dry_run: bool = False,
    ) -> tuple[list[GeoNamesPlace], Optional[ImportResult]]:
        """Fetch candidates and (unless ``dry_run``) persist them.

        Returns the selected places and the import result (``None`` on dry run).
        """
        places = self.fetch_candidates(country)
        if dry_run:
            return places, None
        return places, self.import_to_db(places, overwrite=overwrite)
