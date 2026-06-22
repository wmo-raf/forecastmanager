"""
Publish draft forecasts.

Useful for offices that want a scheduled "review window" then an automatic
publish, or for bulk-publishing from the shell.

Usage::
    python manage.py publish_forecasts                 # publish all drafts
    python manage.py publish_forecasts --date 2026-06-23
    python manage.py publish_forecasts --dry-run
"""

import logging

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date

from forecastmanager.models import Forecast

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Publish draft forecasts (optionally limited to a single date)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            dest="date",
            metavar="YYYY-MM-DD",
            help="Only publish drafts for this forecast date. Defaults to all dates.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Show how many drafts would be published without changing them.",
        )

    def handle(self, *args, **options):
        drafts = Forecast.objects.filter(status=Forecast.STATUS_DRAFT)

        if options.get("date"):
            parsed = parse_date(options["date"])
            if not parsed:
                self.stderr.write(self.style.ERROR(f"Invalid date: {options['date']}"))
                return
            drafts = drafts.filter(forecast_date=parsed)

        count = drafts.count()

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"Would publish {count} draft forecast(s)."))
            return

        updated = drafts.update(status=Forecast.STATUS_PUBLISHED)
        self.stdout.write(self.style.SUCCESS(f"Published {updated} forecast(s)."))
