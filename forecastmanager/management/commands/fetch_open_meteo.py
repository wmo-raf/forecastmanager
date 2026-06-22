"""
Django management command for fetching Open-Meteo forecast data.
This is a thin wrapper around ``climweb.services.open_meteo.OpenMeteoForecastService``.
All business logic lives in the service module so it can be tested and
called independently of Django's management command infrastructure.

Usage::
    python manage.py fetch_open_meteo
    python manage.py fetch_open_meteo --city Nairobi --dry-run
    python manage.py fetch_open_meteo --city Nairobi --city Lagos
    python manage.py fetch_open_meteo --hours 6 12 18
"""

import logging
import sys
from django.core.management.base import BaseCommand
from forecastmanager.services.open_meteo import OpenMeteoForecastService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """Fetch 7-day forecasts from Open-Meteo and save them to forecastmanager."""

    help = (
        "Fetch 7-day city forecasts from the Open-Meteo API "
        "(https://api.open-meteo.com) and save them to the forecastmanager database. No API key required."
    )

    def add_arguments(self, parser):
        """Register command-line arguments."""
        parser.add_argument(
            "--city",
            action="append",
            dest="cities",
            metavar="CITY_NAME",
            help=(
                "Name of a city to fetch forecasts for. Must match a City "
                "record in ClimWeb exactly (case-sensitive). "
                "Repeat for multiple cities. Defaults to all cities."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help=(
                "Log what would be saved without writing anything to the "
                "database. Use this to verify the connection before a live run."
            ),
        )
        parser.add_argument(
            "--hours",
            type=int,
            nargs="+",
            default=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
            metavar="HOUR",
            help=(
                "Hours of day (0-23) to create ForecastPeriods for. "
                "Defaults to 0-23 (all hours)."
            ),
        )

    def handle(self, *args, **options):
        """Entry point called by Django when the command is invoked."""
        service = OpenMeteoForecastService(
            forecast_hours=options["hours"],
        )

        try:
            result = service.run(
                city_filter=options["cities"],
                dry_run=options["dry_run"],
            )
        except (RuntimeError, ValueError) as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            sys.exit(1)

        if result.errors:
            for error in result.errors:
                self.stderr.write(self.style.WARNING(f"  Warning: {error}"))

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run complete. "
                    f"Would have saved {result.saved} period(s), "
                    f"skipped {result.skipped}."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. Saved {result.saved} forecast period(s), "
                    f"skipped {result.skipped}."
                )
            )
