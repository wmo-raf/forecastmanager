"""
Constants and field mappings for the Open-Meteo connector.
All configuration that might need adjustment lives here — API URL,
which hourly variables to request, how Open-Meteo fields map to
forecastmanager parameter keys, and how WMO weather codes map to
yr.no condition symbols.
"""


#: Base URL for the Open-Meteo forecast API.
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

#: Hourly variables requested from Open-Meteo.
HOURLY_VARS: list[str] = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
    "wind_direction_10m",
    "surface_pressure",
    "weathercode",
]

#: Default hours-of-day to create ForecastPeriods for.
#: Open-Meteo returns hourly data; these represent Morning, Afternoon, Evening.
DEFAULT_FORECAST_HOURS: list[int] = [6, 12, 18]

#: Maps Open-Meteo hourly field names to forecastmanager parameter keys.
#: Left  = Open-Meteo field name (what the API returns).
#: Right = ForecastDataParameters.parameter (registered in ClimWeb settings).
FIELD_MAP: dict[str, str] = {
    "temperature_2m": "air_temperature",
    "relative_humidity_2m": "relative_humidity",
    "precipitation": "precipitation_amount",
    "wind_speed_10m": "wind_speed",
    "wind_direction_10m": "wind_from_direction",
    "surface_pressure": "air_pressure_at_sea_level",
}

#: Parameter definitions auto-created in ForecastSetting when not already present.
DEFAULT_PARAMETERS: list[dict] = [
    {
        "parameter": "air_temperature",
        "name": "Air Temperature",
        "parameter_unit": "\u00b0C",
        "parameter_type": "numeric",
    },
    {
        "parameter": "relative_humidity",
        "name": "Relative Humidity",
        "parameter_unit": "%",
        "parameter_type": "numeric",
    },
    {
        "parameter": "precipitation_amount",
        "name": "Precipitation Amount",
        "parameter_unit": "mm",
        "parameter_type": "numeric",
    },
    {
        "parameter": "wind_speed",
        "name": "Wind Speed",
        "parameter_unit": "km/h",
        "parameter_type": "numeric",
    },
    {
        "parameter": "wind_from_direction",
        "name": "Wind Direction",
        "parameter_unit": "\u00b0",
        "parameter_type": "numeric",
    },
    {
        "parameter": "air_pressure_at_sea_level",
        "name": "Air Pressure (Sea Level)",
        "parameter_unit": "hPa",
        "parameter_type": "numeric",
    },
]

#: Maps WMO weather codes (returned by Open-Meteo) to (yr.no symbol, label) pairs.
#: yr.no symbols correspond to icons in forecastmanager/weathericons/*.png.
WMO_CONDITION_MAP: dict[int, tuple[str, str]] = {
    0: ("clearsky_day", "Clear Sky"),
    1: ("fair_day", "Mainly Clear"),
    2: ("partlycloudy_day", "Partly Cloudy"),
    3: ("cloudy", "Overcast"),
    45: ("fog", "Fog"),
    48: ("fog", "Icy Fog"),
    51: ("lightrain", "Light Drizzle"),
    53: ("rain", "Moderate Drizzle"),
    55: ("heavyrain", "Dense Drizzle"),
    61: ("lightrain", "Slight Rain"),
    63: ("rain", "Moderate Rain"),
    65: ("heavyrain", "Heavy Rain"),
    71: ("lightsnow", "Slight Snowfall"),
    73: ("snow", "Moderate Snowfall"),
    75: ("heavysnow", "Heavy Snowfall"),
    77: ("sleet", "Snow Grains"),
    80: ("lightrainshowers_day", "Slight Rain Showers"),
    81: ("rainshowers_day", "Moderate Rain Showers"),
    82: ("heavyrainshowers_day", "Violent Rain Showers"),
    85: ("snowshowers_day", "Slight Snow Showers"),
    86: ("heavysnowshowers_day", "Heavy Snow Showers"),
    95: ("thunderstorm", "Thunderstorm"),
    96: ("thunderstorm", "Thunderstorm with Hail"),
    99: ("thunderstorm", "Thunderstorm with Heavy Hail"),
}

#: Fallback condition used when a WMO code has no entry in WMO_CONDITION_MAP.
UNKNOWN_CONDITION: tuple[str, str] = ("partlycloudy_day", "Unknown Condition")