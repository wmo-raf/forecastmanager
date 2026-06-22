"""
Fetch 7-day forecasts from yr.no for all cities and save them.

The business logic now lives in ``forecastmanager.services.yr`` so it can be
shared with the unified ``generate_auto_forecast`` dispatcher. This command is
kept for backwards compatibility and always uses the yr.no provider with the
admin-configured field map (falling back to identity mapping).
"""

import logging

from django.core.management.base import BaseCommand
from wagtail.models import Site

from forecastmanager.forecast_settings import ForecastSetting
from forecastmanager.providers import PROVIDER_YR
from forecastmanager.services.yr import run_yr_forecast

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = ('Get the weather forecast for the next 7 days from Yr.no '
            'for all cities in the database and save it to the database.')

    def handle(self, *args, **options):
        logger.info("Getting 7 Day Forecast from Yr.no...")

        field_map = None
        try:
            site = Site.objects.get(is_default_site=True)
            forecast_setting = ForecastSetting.for_site(site)
            field_map = forecast_setting.get_provider_field_map(PROVIDER_YR) or None
        except Exception:
            field_map = None

        result = run_yr_forecast(field_map=field_map)

        for error in result.errors:
            self.stderr.write(self.style.WARNING(f"  Warning: {error}"))

        self.stdout.write(self.style.SUCCESS(
            f"Done. Saved {result.saved} forecast period(s), skipped {result.skipped}."
        ))
