import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from forecastmanager.models import Forecast

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clear old forecasts from the database.'

    def handle(self, *args, **options):
        logger.info("Clearing old forecasts from the database...")

        current_time = timezone.localtime()

        # Get all forecasts that are older than the current time
        old_forecasts = Forecast.objects.filter(forecast_date__lt=current_time)

        if not old_forecasts:
            logger.info("No old forecasts found.")
            return

        # Delete the old forecasts
        logger.info(f"Deleting {old_forecasts.count()} old forecasts...")
        old_forecasts.delete()

        logger.info("Old forecasts deleted successfully.")
