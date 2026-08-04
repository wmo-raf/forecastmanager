"""Background tasks for forecastmanager.

These run on Celery, alongside the host project's other scheduled work, so a
long-running provider pull never blocks a web request.

This previously used django-background-tasks, which needs its own
``manage.py process_tasks`` worker. Projects that did not run one — including
the reference ClimWeb deployment — enqueued rows that were never consumed: the
pull silently never happened, and because "is a pull pending?" was answered by
looking for that unconsumed row, the button then disabled itself permanently.
Celery is already running in those deployments, so there is no second queue to
operate and results show up in django-celery-results with everything else.

Concurrency is guarded by a cache key rather than by inspecting the queue. The
key carries a TTL, so a worker that dies mid-pull releases the guard by itself
instead of wedging the UI until someone clears a table by hand.
"""

import logging

from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger(__name__)

#: Cache key held for the duration of a pull.
PULL_LOCK_KEY = "forecastmanager:auto-forecast-pull"

#: Safety net, not an expected duration: a provider pull covering every city
#: takes minutes, and whatever holds this must eventually let go even if the
#: worker is killed (OOM, redeploy) before it can run its cleanup.
PULL_LOCK_TIMEOUT = 30 * 60

#: Registered task name. Kept stable so queued messages and any code that
#: imported this constant keep working.
PULL_TASK_NAME = "forecastmanager.tasks.pull_auto_forecast_task"


def acquire_pull_lock():
    """Claim the right to run a pull. False if one is already in flight.

    ``cache.add`` is atomic on Redis and memcached, so two simultaneous clicks
    cannot both win.
    """
    return bool(cache.add(PULL_LOCK_KEY, "1", PULL_LOCK_TIMEOUT))


def release_pull_lock():
    cache.delete(PULL_LOCK_KEY)


def pull_is_pending():
    return cache.get(PULL_LOCK_KEY) is not None


@shared_task(name=PULL_TASK_NAME)
def pull_auto_forecast_task(setting_pk):
    """Pull forecasts from the configured external provider.

    Args:
        setting_pk: Primary key of the ForecastSetting to run with. Passed as a
            primitive rather than an instance so the message stays serialisable.
    """
    # Imported lazily so this module stays import-light and avoids circulars.
    from forecastmanager.forecast_settings import ForecastSetting
    from forecastmanager.services.auto_forecast import (
        AutoForecastError,
        run_auto_forecast,
    )

    try:
        setting = ForecastSetting.objects.filter(pk=setting_pk).first()
        if setting is None:
            logger.error(
                "ForecastSetting %s not found; aborting forecast pull.", setting_pk
            )
            return

        try:
            result = run_auto_forecast(setting)
        except AutoForecastError as exc:
            # A configuration or provider problem rather than a bug: log it
            # plainly instead of raising a traceback into the worker.
            logger.error("Forecast pull failed: %s", exc)
            return

        for error in result.errors:
            logger.warning("  Pull warning: %s", error)

        logger.info(
            "Forecast pull complete: saved %s period(s), skipped %s.",
            result.saved,
            result.skipped,
        )
    finally:
        # Always release, including on an unexpected exception, so one failure
        # doesn't block the next attempt until the TTL expires.
        release_pull_lock()
