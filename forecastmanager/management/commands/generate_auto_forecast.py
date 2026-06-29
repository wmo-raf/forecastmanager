"""
Unified automated-forecast command.

Reads the active provider and its parameter mapping from ForecastSetting
(configured in the Wagtail admin under City Forecast -> Settings -> Forecast
Source) and dispatches to the matching provider service.

Usage::
    python manage.py generate_auto_forecast
    python manage.py generate_auto_forecast --city Nairobi --dry-run
    python manage.py generate_auto_forecast --hours 6 12 18
"""

import logging
import sys

from django.core.management.base import BaseCommand
from wagtail.models import Site

from forecastmanager.forecast_settings import ForecastSetting
from forecastmanager.providers import PROVIDER_OPEN_METEO, PROVIDER_YR
from forecastmanager.services.open_meteo import OpenMeteoForecastService
from forecastmanager.services.yr import run_yr_forecast

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Fetch automated forecasts using the provider selected in the Wagtail "
        "admin (City Forecast -> Settings -> Forecast Source) and the "
        "admin-configured parameter mapping."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--city",
            action="append",
            dest="cities",
            metavar="CITY_NAME",
            help="Restrict to a city (repeat for multiple). Defaults to all cities.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Log what would be saved without writing to the database.",
        )
        parser.add_argument(
            "--hours",
            type=int,
            nargs="+",
            default=[0, 3, 6, 9, 12, 15, 18, 21],
            metavar="HOUR",
            help="Hours of day to create ForecastPeriods for (Open-Meteo only). Defaults to 3-hourly (0,3,...,21).",
        )

    def handle(self, *args, **options):
        try:
            site = Site.objects.get(is_default_site=True)
        except Site.DoesNotExist:
            self.stderr.write(self.style.ERROR("No default Wagtail site found."))
            sys.exit(1)

        forecast_setting = ForecastSetting.for_site(site)
        if not forecast_setting:
            self.stderr.write(self.style.ERROR("No ForecastSetting configured."))
            sys.exit(1)

        if not forecast_setting.enable_auto_forecast:
            self.stderr.write(self.style.WARNING("Automated forecasts are disabled in settings."))
            return

        provider = forecast_setting.forecast_provider
        field_map = forecast_setting.get_provider_field_map(provider)

        self.stdout.write(self.style.NOTICE(f"Provider: {provider}"))
        if field_map:
            self.stdout.write(self.style.NOTICE(f"Using {len(field_map)} configured mapping(s)."))
        else:
            self.stdout.write(self.style.WARNING(
                "No parameter mappings configured for this provider; "
                "falling back to built-in defaults."
            ))

        if provider == PROVIDER_OPEN_METEO:
            service = OpenMeteoForecastService(
                forecast_hours=options["hours"],
                field_map=field_map or None,
            )
            try:
                result = service.run(
                    city_filter=options["cities"],
                    dry_run=options["dry_run"],
                )
            except (RuntimeError, ValueError) as exc:
                self.stderr.write(self.style.ERROR(str(exc)))
                sys.exit(1)
        elif provider == PROVIDER_YR:
            result = run_yr_forecast(
                field_map=field_map or None,
                city_filter=options["cities"],
                dry_run=options["dry_run"],
            )
        else:
            self.stderr.write(self.style.ERROR(f"Unknown provider: {provider}"))
            sys.exit(1)

        for error in result.errors:
            self.stderr.write(self.style.WARNING(f"  Warning: {error}"))

        verb = "Would have saved" if options["dry_run"] else "Saved"
        self.stdout.write(self.style.SUCCESS(
            f"Done. {verb} {result.saved} forecast period(s), skipped {result.skipped}."
        ))
