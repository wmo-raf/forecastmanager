from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase

from forecastmanager import tasks


class PullLockTests(SimpleTestCase):
    """The guard that stops two pulls running at once.

    Before 0.6.7 this was "does an unconsumed django-background-tasks row
    exist?", which meant a queue nobody consumed disabled the button forever.
    A cache key with a TTL cannot get stuck that way.
    """

    def setUp(self):
        cache.delete(tasks.PULL_LOCK_KEY)
        self.addCleanup(cache.delete, tasks.PULL_LOCK_KEY)

    def test_nothing_pending_on_a_clean_slate(self):
        self.assertFalse(tasks.pull_is_pending())

    def test_acquiring_marks_a_pull_as_pending(self):
        self.assertTrue(tasks.acquire_pull_lock())
        self.assertTrue(tasks.pull_is_pending())

    def test_second_acquire_is_refused(self):
        """Two quick clicks must not both enqueue."""
        self.assertTrue(tasks.acquire_pull_lock())
        self.assertFalse(tasks.acquire_pull_lock())

    def test_releasing_allows_the_next_pull(self):
        tasks.acquire_pull_lock()
        tasks.release_pull_lock()

        self.assertFalse(tasks.pull_is_pending())
        self.assertTrue(tasks.acquire_pull_lock())

    def test_release_is_safe_when_nothing_is_held(self):
        tasks.release_pull_lock()  # must not raise
        self.assertFalse(tasks.pull_is_pending())

    def test_lock_is_written_with_an_expiry(self):
        """Without a TTL, a worker killed mid-pull would wedge the button."""
        with mock.patch.object(cache, "add", return_value=True) as add:
            tasks.acquire_pull_lock()

        args, _kwargs = add.call_args
        self.assertEqual(args[0], tasks.PULL_LOCK_KEY)
        self.assertEqual(args[2], tasks.PULL_LOCK_TIMEOUT)
        self.assertGreater(tasks.PULL_LOCK_TIMEOUT, 0)


class PullTaskTests(SimpleTestCase):
    """The task must always release the lock, however it exits."""

    def setUp(self):
        cache.delete(tasks.PULL_LOCK_KEY)
        self.addCleanup(cache.delete, tasks.PULL_LOCK_KEY)

    def test_task_is_registered_under_the_documented_name(self):
        self.assertEqual(tasks.pull_auto_forecast_task.name, tasks.PULL_TASK_NAME)

    def test_lock_is_released_when_the_setting_is_missing(self):
        tasks.acquire_pull_lock()

        with mock.patch(
            "forecastmanager.forecast_settings.ForecastSetting"
        ) as setting_model:
            setting_model.objects.filter.return_value.first.return_value = None
            tasks.pull_auto_forecast_task(999)

        self.assertFalse(tasks.pull_is_pending())

    def test_lock_is_released_after_an_unexpected_error(self):
        """Otherwise one crash blocks every pull until the TTL expires."""
        tasks.acquire_pull_lock()

        with mock.patch(
            "forecastmanager.forecast_settings.ForecastSetting"
        ) as setting_model:
            setting_model.objects.filter.side_effect = RuntimeError("database gone")

            with self.assertRaises(RuntimeError):
                tasks.pull_auto_forecast_task(1)

        self.assertFalse(tasks.pull_is_pending())

    def test_lock_is_released_after_a_provider_failure(self):
        tasks.acquire_pull_lock()

        from forecastmanager.services.auto_forecast import AutoForecastError

        with mock.patch(
            "forecastmanager.forecast_settings.ForecastSetting"
        ) as setting_model, mock.patch(
            "forecastmanager.services.auto_forecast.run_auto_forecast"
        ) as run:
            setting_model.objects.filter.return_value.first.return_value = mock.Mock()
            run.side_effect = AutoForecastError("provider unreachable")
            tasks.pull_auto_forecast_task(1)

        self.assertFalse(tasks.pull_is_pending())

    def test_lock_is_released_on_success(self):
        tasks.acquire_pull_lock()

        with mock.patch(
            "forecastmanager.forecast_settings.ForecastSetting"
        ) as setting_model, mock.patch(
            "forecastmanager.services.auto_forecast.run_auto_forecast"
        ) as run:
            setting_model.objects.filter.return_value.first.return_value = mock.Mock()
            run.return_value = mock.Mock(errors=[], saved=3, skipped=1)
            tasks.pull_auto_forecast_task(1)

        self.assertFalse(tasks.pull_is_pending())


class WeatherIconsViewTests(SimpleTestCase):
    """The map preloads every icon this endpoint returns.

    Before this change it returned the whole 83-symbol yr.no catalogue, so a
    first paint cost 83 image requests no matter how few conditions the site
    actually used. Only conditions configured on the ForecastSetting can ever
    reach the map, so anything outside that list is dead weight.
    """

    def setUp(self):
        from forecastmanager.views import WeatherIconsView

        self.view = WeatherIconsView()
        self.request = mock.Mock(query_params={})

        patcher = mock.patch(
            "forecastmanager.views.get_full_url", side_effect=lambda _r, url: url
        )
        self.get_full_url = patcher.start()
        self.addCleanup(patcher.stop)

    def configure(self, *symbols):
        """Point ForecastSetting.for_request at a settings object with these symbols."""
        patcher = mock.patch("forecastmanager.views.ForecastSetting")
        setting_model = patcher.start()
        self.addCleanup(patcher.stop)

        fm_settings = mock.Mock()
        fm_settings.weather_conditions.all.return_value = [
            mock.Mock(symbol=symbol) for symbol in symbols
        ]
        setting_model.for_request.return_value = fm_settings
        return setting_model

    def ids_returned(self):
        return [icon["id"] for icon in self.view.get(self.request).data]

    def test_only_configured_conditions_are_returned(self):
        self.configure("clearsky_day", "cloudy", "lightrain")

        self.assertCountEqual(
            self.ids_returned(), ["clearsky_day", "cloudy", "lightrain"]
        )

    def test_response_keeps_its_shape(self):
        self.configure("cloudy")

        icon = self.view.get(self.request).data[0]

        self.assertEqual(sorted(icon), ["id", "name", "url"])
        self.assertEqual(icon["id"], "cloudy")
        self.assertTrue(icon["url"].endswith("weathericons/cloudy.png"))

    def test_map_icons_are_raster(self):
        """MapLibre loadImage cannot take SVG - an .svg url here breaks the map."""
        self.configure("cloudy", "fog")

        for icon in self.view.get(self.request).data:
            self.assertTrue(icon["url"].endswith(".png"), icon["url"])

    def test_unconfigured_site_still_gets_the_full_catalogue(self):
        """A fresh install has no conditions yet; an empty map is worse than a slow one."""
        self.configure()

        self.assertEqual(len(self.ids_returned()), 83)

    def test_missing_settings_fall_back_rather_than_returning_nothing(self):
        setting_model = self.configure()
        setting_model.for_request.return_value = None

        self.assertEqual(len(self.ids_returned()), 83)

    def test_settings_lookup_failure_falls_back(self):
        setting_model = self.configure()
        setting_model.for_request.side_effect = RuntimeError("no site for request")

        self.assertEqual(len(self.ids_returned()), 83)

    def test_symbols_query_narrows_the_configured_set(self):
        self.configure("clearsky_day", "cloudy", "lightrain")
        self.request.query_params = {"symbols": "cloudy,lightrain"}

        self.assertCountEqual(self.ids_returned(), ["cloudy", "lightrain"])

    def test_symbols_query_cannot_widen_beyond_what_is_configured(self):
        """Otherwise a client could pull icons the site never configured."""
        self.configure("cloudy")
        self.request.query_params = {"symbols": "cloudy,heavysnow"}

        self.assertEqual(self.ids_returned(), ["cloudy"])

    def test_symbols_query_tolerates_spacing_and_empties(self):
        self.configure("clearsky_day", "cloudy")
        self.request.query_params = {"symbols": " cloudy , ,clearsky_day,"}

        self.assertCountEqual(self.ids_returned(), ["cloudy", "clearsky_day"])

    def test_unknown_symbols_are_ignored_not_echoed(self):
        self.configure("cloudy", "not_a_real_symbol")

        self.assertEqual(self.ids_returned(), ["cloudy"])


class CityForecastGeojsonFeatureTests(SimpleTestCase):
    """One city forecast without a condition used to raise AttributeError,
    which took down the whole home map feed it was serialized into."""

    def make_city_forecast(self, condition=None):
        from datetime import date, time

        from django.contrib.gis.geos import Point

        from forecastmanager.forecast_settings import ForecastPeriod
        from forecastmanager.models import City, CityForecast, Forecast

        period = ForecastPeriod(forecast_effective_time=time(6, 0), label="Morning")
        forecast = Forecast(forecast_date=date(2026, 10, 15), effective_period=period)
        city = City(name="Nairobi", slug="nairobi", location=Point(36.8, -1.3))
        return CityForecast(parent=forecast, city=city, condition=condition)

    def test_missing_condition_serializes_with_empty_condition_fields(self):
        feature = self.make_city_forecast().get_geojson_feature()

        self.assertEqual(feature["properties"]["city"], "Nairobi")
        self.assertIsNone(feature["properties"]["condition"])
        self.assertIsNone(feature["properties"]["condition_label"])
        self.assertIsNone(feature["properties"]["condition_symbol_url"])
