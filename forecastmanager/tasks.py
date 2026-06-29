"""
Background tasks for forecastmanager.

These run in a separate ``process_tasks`` worker (django-background-tasks), not
in the web request, so long-running provider pulls don't block the site.

Run the worker alongside the web server::

    python manage.py process_tasks
"""

import logging

from background_task import background

logger = logging.getLogger(__name__)

#: Registered task name (module path + function name). Used to detect whether a
#: pull is already queued or running, so we don't enqueue duplicates.
PULL_TASK_NAME = "forecastmanager.tasks.pull_auto_forecast_task"


@background(schedule=0)
def pull_auto_forecast_task(setting_pk):
    """
    Pull forecasts from the configured external provider in the background.

    Args:
        setting_pk: Primary key of the ForecastSetting to run with. Passed as a
            primitive (not the instance) because background-task arguments must
            be JSON-serialisable.
    """
    # Imported lazily so this module stays import-light and avoids circulars.
    from forecastmanager.forecast_settings import ForecastSetting
    from forecastmanager.services.auto_forecast import run_auto_forecast, AutoForecastError

    setting = ForecastSetting.objects.filter(pk=setting_pk).first()
    if setting is None:
        logger.error("ForecastSetting %s not found; aborting background pull.", setting_pk)
        return

    try:
        result = run_auto_forecast(setting)
    except AutoForecastError as exc:
        logger.error("Background forecast pull failed: %s", exc)
        return

    for error in result.errors:
        logger.warning("  Pull warning: %s", error)

    logger.info(
        "Background forecast pull complete: saved %s period(s), skipped %s.",
        result.saved,
        result.skipped,
    )
