"""
Django management command for importing cities from GeoNames.

Business logic lives in ``forecastmanager.services.geonames`` so it can be
tested and called independently of Django's management infrastructure.

Usage::
    python manage.py import_geonames_cities --country MW
    python manage.py import_geonames_cities --country KE --max 150 --dry-run
    python manage.py import_geonames_cities --country MW --overwrite
    python manage.py import_geonames_cities --country MW --username myuser
"""

import sys

from django.core.management.base import BaseCommand

from forecastmanager.forecast_settings import ForecastSetting
from forecastmanager.services.geonames import (
    GeoNamesClient,
    GeoNamesError,
    GeoNamesImportService,
)
from forecastmanager.services.geonames.constants import DEFAULT_MAX_CITIES


class Command(BaseCommand):
    help = (
        "Import cities for a country from the GeoNames web service. "
        "Selects administrative seats (capitals, district centres) plus the "
        "highest-population places, capped at a maximum."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--country",
            required=True,
            metavar="CC",
            help="ISO 3166 alpha-2 country code, e.g. MW.",
        )
        parser.add_argument(
            "--max",
            type=int,
            default=DEFAULT_MAX_CITIES,
            dest="max_cities",
            metavar="N",
            help=f"Maximum number of cities to import (default {DEFAULT_MAX_CITIES}).",
        )
        parser.add_argument(
            "--username",
            default=None,
            help="GeoNames username. Defaults to the one saved in Forecast Settings.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            default=False,
            help="Update the location of cities that already exist instead of skipping them.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="List the cities that would be imported without writing anything.",
        )

    def handle(self, *args, **options):
        username = options["username"]
        if not username:
            fm_settings = ForecastSetting.objects.first()
            username = fm_settings.geonames_username if fm_settings else None

        if not username:
            self.stderr.write(self.style.ERROR(
                "No GeoNames username provided. Pass --username or set one under "
                "Forecast Settings > Other Settings."
            ))
            sys.exit(1)

        service = GeoNamesImportService(
            GeoNamesClient(username=username),
            max_cities=options["max_cities"],
        )

        try:
            places, result = service.run(
                country=options["country"],
                overwrite=options["overwrite"],
                dry_run=options["dry_run"],
            )
        except GeoNamesError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            sys.exit(1)

        if options["dry_run"]:
            for place in places:
                self.stdout.write(
                    f"  {place.feature_code:<5} {place.name} "
                    f"(pop {place.population}, {place.lat}, {place.lon})"
                )
            self.stdout.write(self.style.WARNING(
                f"Dry run complete. Would import {len(places)} city(ies)."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Done. Created {result.created}, updated {result.updated}, "
                f"skipped {result.skipped} (selected {len(places)})."
            ))
