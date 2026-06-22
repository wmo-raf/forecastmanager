"""
Registry of automated forecast providers and the source fields each one exposes.

This is the single source of truth used by:
  * the ``forecast_provider`` dropdown on ForecastSetting
  * the ``source_field`` dropdown on the parameter-mapping inline
  * the service layer, when resolving an admin-configured field map

To add a new provider, append an entry to ``PROVIDERS`` and wire a service
for it in the ``generate_auto_forecast`` dispatcher command.
"""

from django.utils.translation import gettext_lazy as _

#: Provider keys. Kept as module-level constants so other modules can refer to
#: them without magic strings.
PROVIDER_YR = "yr"
PROVIDER_OPEN_METEO = "open_meteo"

#: Provider definitions.
#:
#: ``fields`` is the list of source variables a provider can supply that an
#: admin may map onto a ForecastDataParameter. Each field is a dict with:
#:   value -- the raw field key the provider/service understands
#:   label -- human friendly label shown in the admin dropdown
#:
#: Note: condition/weather-code fields are intentionally excluded here because
#: they drive the WeatherCondition lookup, not a numeric/text data parameter.
PROVIDERS: dict[str, dict] = {
    PROVIDER_YR: {
        "label": _("yr.no (Met Norway)"),
        "fields": [
            {"value": "air_temperature", "label": _("Air Temperature")},
            {"value": "air_temperature_min", "label": _("Minimum Air Temperature")},
            {"value": "air_temperature_max", "label": _("Maximum Air Temperature")},
            {"value": "air_pressure_at_sea_level", "label": _("Air Pressure (Sea level)")},
            {"value": "relative_humidity", "label": _("Relative Humidity")},
            {"value": "dew_point_temperature", "label": _("Dew Point Temperature")},
            {"value": "wind_speed", "label": _("Wind Speed")},
            {"value": "wind_from_direction", "label": _("Wind Direction")},
            {"value": "precipitation_amount", "label": _("Precipitation Amount")},
        ],
    },
    PROVIDER_OPEN_METEO: {
        "label": _("Open-Meteo"),
        "fields": [
            {"value": "temperature_2m", "label": _("Temperature (2 m)")},
            {"value": "relative_humidity_2m", "label": _("Relative Humidity (2 m)")},
            {"value": "dew_point_2m", "label": _("Dew Point (2 m)")},
            {"value": "apparent_temperature", "label": _("Apparent Temperature")},
            {"value": "precipitation", "label": _("Precipitation")},
            {"value": "rain", "label": _("Rain")},
            {"value": "wind_speed_10m", "label": _("Wind Speed (10 m)")},
            {"value": "wind_direction_10m", "label": _("Wind Direction (10 m)")},
            {"value": "wind_gusts_10m", "label": _("Wind Gusts (10 m)")},
            {"value": "surface_pressure", "label": _("Surface Pressure")},
            {"value": "pressure_msl", "label": _("Pressure (Mean Sea Level)")},
            {"value": "cloud_cover", "label": _("Cloud Cover")},
        ],
    },
}


def get_provider_choices() -> list[tuple[str, str]]:
    """Return ``(value, label)`` choices for the provider dropdown."""
    return [(key, cfg["label"]) for key, cfg in PROVIDERS.items()]


def get_provider_field_choices(provider: str) -> list[tuple[str, str]]:
    """Return ``(value, label)`` choices for one provider's source fields."""
    cfg = PROVIDERS.get(provider, {})
    return [(f["value"], f["label"]) for f in cfg.get("fields", [])]


def get_all_field_options() -> list[dict]:
    """
    Return every provider field as a flat list, each tagged with its provider.

    Used by the source-field widget so a single ``<select>`` can hold all
    options and be filtered client-side by the chosen provider.
    """
    options = []
    for provider, cfg in PROVIDERS.items():
        for f in cfg.get("fields", []):
            options.append({
                "provider": provider,
                "value": f["value"],
                "label": f["label"],
            })
    return options
