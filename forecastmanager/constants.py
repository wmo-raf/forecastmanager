from django.utils.translation import gettext_lazy as _

# extracted from https://nrkno.github.io/yr-weather-symbols/
WEATHER_CONDITION_CHOICES = (
    ('clearsky_day', _('Clear sky Day')),  # 01d
    ('clearsky_night', _('Clear sky Night')),  # 01n
    ('clearsky_polartwilight', _('Clear sky Polar Twilight')),  # 01m

    ('fair_day', _('Fair Day')),  # 02d
    ('fair_night', _('Fair Night')),  # 02n
    ('fair_polartwilight', _('Fair Polar Twilight')),  # 02m

    ('partlycloudy_day', _('Partly Cloudy Day')),  # 03d
    ('partlycloudy_night', _('Partly Cloudy Night')),  # 03n
    ('partlycloudy_polartwilight', _('Partly Cloudy Polar Twilight')),

    ('cloudy', _('Cloudy')),  # 04

    ('rainshowers_day', _('Rain Showers Day')),  # 05d
    ('rainshowers_night', _('Rain Showers Night')),  # 05n
    ('rainshowers_polartwilight', _('Rain Showers Polar Twilight')),  # 05m

    ('rainshowersandthunder_day', _('Rain Showers and Thunder Day')),  # 06d
    ('rainshowersandthunder_night', _('Rain Showers and Thunder Night')),  # 06n
    ('rainshowersandthunder_polartwilight', _('Rain Showers and Thunder Polar Twilight')),  # 06m

    ('sleetshowers_day', _('Sleet Showers Day')),  # 07d
    ('sleetshowers_night', _('Sleet Showers Night')),  # 07n
    ('sleetshowers_polartwilight', _('Sleet Showers Polar Twilight')),

    ('snowshowers_day', _('Snow Showers Day')),  # 08d
    ('snowshowers_night', _('Snow Showers Night')),  # 08n
    ('snowshowers_polartwilight', _('Snow Showers Polar Twilight')),  # 08m

    ('rain', _('Rain')),  # 09
    ('heavyrain', _('Heavy Rain')),  # 10
    ('heavyrainandthunder', _('Heavy Rain and Thunder')),  # 11
    ('sleet', _('Sleet')),  # 12
    ('snow', _('Snow')),  # 13
    ('snowandthunder', _('Snow and Thunder')),  # 14
    ('fog', _('Fog')),  # 15

    ('sleetshowersandthunder_day', _('Sleet Showers and Thunder Day')),  # 20d
    ('sleetshowersandthunder_night', _('Sleet Showers and Thunder Night')),  # 20n
    ('sleetshowersandthunder_polartwilight', _('Sleet Showers and Thunder Polar Twilight')),  # 20m

    ('snowshowersandthunder_day', _('Snow Showers and Thunder Day')),  # 21d
    ('snowshowersandthunder_night', _('Snow Showers and Thunder Night')),  # 21n
    ('snowshowersandthunder_polartwilight', _('Snow Showers and Thunder Polar Twilight')),  # 21m

    ('rainandthunder', _('Rain and Thunder')),  # 22
    ('sleetandthunder', _('Sleet and Thunder')),  # 23

    ('lightrainshowersandthunder_day', _('Light Rain Showers and Thunder Day')),  # 24d
    ('lightrainshowersandthunder_night', _('Light Rain Showers and Thunder Night')),  # 24n
    ('lightrainshowersandthunder_polartwilight', _('Light Rain Showers and Thunder Polar Twilight')),  # 24m

    ('heavyrainshowersandthunder_day', _('Heavy Rain Showers and Thunder Day')),  # 25d
    ('heavyrainshowersandthunder_night', _('Heavy Rain Showers and Thunder Night')),  # 25n
    ('heavyrainshowersandthunder_polartwilight', _('Heavy Rain Showers and Thunder Polar Twilight')),  # 25m

    ('lightsleetshowersandthunder_day', _('Light Sleet Showers and Thunder Day')),  # 26d
    ('lightsleetshowersandthunder_night', _('Light Sleet Showers and Thunder Night')),  # 26n
    ('lightsleetshowersandthunder_polartwilight', _('Light Sleet Showers and Thunder Polar Twilight')),  # 26m

    ('heavysleetshowersandthunder_day', _('Heavy Sleet Showers and Thunder Day')),  # 27d
    ('heavysleetshowersandthunder_night', _('Heavy Sleet Showers and Thunder Night')),  # 27n
    ('heavysleetshowersandthunder_polartwilight', _('Heavy Sleet Showers and Thunder Polar Twilight')),  # 27m

    ('lightsnowshowersandthunder_day', _('Light Snow Showers and Thunder Day')),  # 28d
    ('lightsnowshowersandthunder_night', _('Light Snow Showers and Thunder Night')),  # 28n
    ('lightsnowshowersandthunder_polartwilight', _('Light Snow Showers and Thunder Polar Twilight')),  # 28m

    ('heavysnowshowersandthunder_day', _('Heavy Snow Showers and Thunder Day')),  # 29d
    ('heavysnowshowersandthunder_night', _('Heavy Snow Showers and Thunder Night')),  # 29n
    ('heavysnowshowersandthunder_polartwilight', _('Heavy Snow Showers and Thunder Polar Twilight')),  # 29m

    ('lightrainandthunder', _('Light Rain and Thunder')),  # 30
    ('lightsleetandthunder', _('Light Sleet and Thunder')),  # 31

    ('heavysleetandthunder', _('Heavy Sleet and Thunder')),  # 32
    ('lightsnowandthunder', _('Light Snow and Thunder')),  # 33
    ('heavysnowandthunder', _('Heavy Snow and Thunder')),  # 34

    ('lightrainshowers_day', _('Light Rain Showers Day')),  # 40d
    ('lightrainshowers_night', _('Light Rain Showers Night')),  # 40n
    ('lightrainshowers_polartwilight', _('Light Rain Showers Polar Twilight')),  # 40m

    ('heavyrainshowers_day', _('Heavy Rain Showers Day')),  # 41d
    ('heavyrainshowers_night', _('Heavy Rain Showers Night')),  # 41n
    ('heavyrainshowers_polartwilight', _('Heavy Rain Showers Polar Twilight')),  # 41m

    ('lightsleetshowers_day', _('Light Sleet Showers Day')),  # 42d
    ('lightsleetshowers_night', _('Light Sleet Showers Night')),  # 42n
    ('lightsleetshowers_polartwilight', _('Light Sleet Showers Polar Twilight')),  # 42m

    ('heavysleetshowers_day', _('Heavy Sleet Showers Day')),  # 43d
    ('heavysleetshowers_night', _('Heavy Sleet Showers Night')),  # 43n
    ('heavysleetshowers_polartwilight', _('Heavy Sleet Showers Polar Twilight')),  # 43m

    ('lightsnowshowers_day', _('Light Snow Showers Day')),  # 44d
    ('lightsnowshowers_night', _('Light Snow Showers Night')),  # 44n
    ('lightsnowshowers_polartwilight', _('Light Snow Showers Polar Twilight')),  # 44m

    ('heavysnowshowers_day', _('Heavy Snow Showers Day')),  # 45d
    ('heavysnowshowers_night', _('Heavy Snow Showers Night')),  # 45n
    ('heavysnowshowers_polartwilight', _('Heavy Snow Showers Polar Twilight')),  # 45m

    ('lightrain', _('Light Rain')),  # 46
    ('lightsleet', _('Light Sleet')),  # 47
    ('heavysleet', _('Heavy Sleet')),  # 48
    ('lightsnow', _('Light Snow')),  # 49
    ('heavysnow', _('Heavy Snow')),  # 50
)

WEATHER_PARAMETERS = [
    {
        "name": "air_temperature_max",
        "label": "Maximum Air Temperature",
        "unit": "°C",
        "data_type": "int"
    },
    {
        "name": "air_temperature_min",
        "label": "Minimum Air Temperature",
        "unit": "°C",
        "data_type": "int"
    },
    {
        "name": "air_temperature",
        "label": "Air Temperature",
        "unit": "°C",
        "data_type": "int"
    },
    {
        "name": "dew_point_temperature",
        "label": "Dew Point Temperature",
        "unit": "°C",
        "data_type": "int"
    },
    {
        "name": "precipitation_amount",
        "label": "Precipitation Amount",
        "unit": "mm",
        "data_type": "float"
    },
    {
        "name": "air_pressure_at_sea_level",
        "label": "Air Pressure (Sea level)",
        "unit": "hPa",
        "data_type": "int"
    },
    {
        "name": "wind_speed",
        "label": "Wind Speed",
        "unit": "m/s",
        "data_type": "int"
    },
    {
        "name": "wind_from_direction",
        "label": "Wind Direction",
        "unit": "°",
        "data_type": "int"
    },
    {
        "name": "relative_humidity",
        "label": "Relative Humidity",
        "unit": "%",
        "data_type": "int"
    },
    {
        "name": "sunrise",
        "label": "Sunrise",
    },
    {
        "name": "sunset",
        "label": "Sunset",
    },
    {
        "name": "moonrise",
        "label": "Moonrise",
    },
    {
        "name": "moonset",
        "label": "Moonset",
    },
]

WEATHER_PARAMETER_CHOICES = [(param['name'], _(param['label'])) for param in WEATHER_PARAMETERS]

WEATHER_PARAMETERS_AS_DICT = {param['name']: param for param in WEATHER_PARAMETERS}
