from django.utils.translation import gettext_lazy as _

# extracted from https://nrkno.github.io/yr-weather-symbols/
WEATHER_CONDITIONS = [
    {'id': 'clearsky_day', 'name': 'Clear sky Day'},
    {'id': 'clearsky_night', 'name': 'Clear sky Night'},
    {'id': 'clearsky_polartwilight', 'name': 'Clear sky Polar Twilight'},

    {'id': 'fair_day', 'name': 'Fair Day'},
    {'id': 'fair_night', 'name': 'Fair Night'},
    {'id': 'fair_polartwilight', 'name': 'Fair Polar Twilight'},

    {'id': 'partlycloudy_day', 'name': 'Partly Cloudy Day'},
    {'id': 'partlycloudy_night', 'name': 'Partly Cloudy Night'},
    {'id': 'partlycloudy_polartwilight', 'name': 'Partly Cloudy Polar Twilight'},

    {'id': 'cloudy', 'name': 'Cloudy'},

    {'id': 'rainshowers_day', 'name': 'Rain Showers Day'},
    {'id': 'rainshowers_night', 'name': 'Rain Showers Night'},
    {'id': 'rainshowers_polartwilight', 'name': 'Rain Showers Polar Twilight'},

    {'id': 'rainshowersandthunder_day', 'name': 'Rain Showers and Thunder Day'},
    {'id': 'rainshowersandthunder_night', 'name': 'Rain Showers and Thunder Night'},
    {'id': 'rainshowersandthunder_polartwilight', 'name': 'Rain Showers and Thunder Polar Twilight'},

    {'id': 'sleetshowers_day', 'name': 'Sleet Showers Day'},
    {'id': 'sleetshowers_night', 'name': 'Sleet Showers Night'},
    {'id': 'sleetshowers_polartwilight', 'name': 'Sleet Showers Polar Twilight'},

    {'id': 'snowshowers_day', 'name': 'Snow Showers Day'},
    {'id': 'snowshowers_night', 'name': 'Snow Showers Night'},
    {'id': 'snowshowers_polartwilight', 'name': 'Snow Showers Polar Twilight'},

    {'id': 'rain', 'name': 'Rain'}, {'id': 'heavyrain', 'name': 'Heavy Rain'},

    {'id': 'heavyrainandthunder', 'name': 'Heavy Rain and Thunder'}, {'id': 'sleet', 'name': 'Sleet'},

    {'id': 'snow', 'name': 'Snow'}, {'id': 'snowandthunder', 'name': 'Snow and Thunder'},

    {'id': 'fog', 'name': 'Fog'},

    {'id': 'sleetshowersandthunder_day', 'name': 'Sleet Showers and Thunder Day'},
    {'id': 'sleetshowersandthunder_night', 'name': 'Sleet Showers and Thunder Night'},
    {'id': 'sleetshowersandthunder_polartwilight', 'name': 'Sleet Showers and Thunder Polar Twilight'},

    {'id': 'snowshowersandthunder_day', 'name': 'Snow Showers and Thunder Day'},
    {'id': 'snowshowersandthunder_night', 'name': 'Snow Showers and Thunder Night'},
    {'id': 'snowshowersandthunder_polartwilight', 'name': 'Snow Showers and Thunder Polar Twilight'},

    {'id': 'rainandthunder', 'name': 'Rain and Thunder'},

    {'id': 'sleetandthunder', 'name': 'Sleet and Thunder'},

    {'id': 'lightrainshowersandthunder_day', 'name': 'Light Rain Showers and Thunder Day'},
    {'id': 'lightrainshowersandthunder_night', 'name': 'Light Rain Showers and Thunder Night'},
    {'id': 'lightrainshowersandthunder_polartwilight', 'name': 'Light Rain Showers and Thunder Polar Twilight'},

    {'id': 'heavyrainshowersandthunder_day', 'name': 'Heavy Rain Showers and Thunder Day'},
    {'id': 'heavyrainshowersandthunder_night', 'name': 'Heavy Rain Showers and Thunder Night'},
    {'id': 'heavyrainshowersandthunder_polartwilight', 'name': 'Heavy Rain Showers and Thunder Polar Twilight'},

    {'id': 'lightsleetshowersandthunder_day', 'name': 'Light Sleet Showers and Thunder Day'},
    {'id': 'lightsleetshowersandthunder_night', 'name': 'Light Sleet Showers and Thunder Night'},
    {'id': 'lightsleetshowersandthunder_polartwilight', 'name': 'Light Sleet Showers and Thunder Polar Twilight'},

    {'id': 'heavysleetshowersandthunder_day', 'name': 'Heavy Sleet Showers and Thunder Day'},
    {'id': 'heavysleetshowersandthunder_night', 'name': 'Heavy Sleet Showers and Thunder Night'},
    {'id': 'heavysleetshowersandthunder_polartwilight', 'name': 'Heavy Sleet Showers and Thunder Polar Twilight'},

    {'id': 'lightsnowshowersandthunder_day', 'name': 'Light Snow Showers and Thunder Day'},
    {'id': 'lightsnowshowersandthunder_night', 'name': 'Light Snow Showers and Thunder Night'},
    {'id': 'lightsnowshowersandthunder_polartwilight', 'name': 'Light Snow Showers and Thunder Polar Twilight'},

    {'id': 'heavysnowshowersandthunder_day', 'name': 'Heavy Snow Showers and Thunder Day'},
    {'id': 'heavysnowshowersandthunder_night', 'name': 'Heavy Snow Showers and Thunder Night'},
    {'id': 'heavysnowshowersandthunder_polartwilight', 'name': 'Heavy Snow Showers and Thunder Polar Twilight'},

    {'id': 'lightrainandthunder', 'name': 'Light Rain and Thunder'},
    {'id': 'lightsleetandthunder', 'name': 'Light Sleet and Thunder'},
    {'id': 'heavysleetandthunder', 'name': 'Heavy Sleet and Thunder'},
    {'id': 'lightsnowandthunder', 'name': 'Light Snow and Thunder'},
    {'id': 'heavysnowandthunder', 'name': 'Heavy Snow and Thunder'},
    {'id': 'lightrainshowers_day', 'name': 'Light Rain Showers Day'},
    {'id': 'lightrainshowers_night', 'name': 'Light Rain Showers Night'},
    {'id': 'lightrainshowers_polartwilight', 'name': 'Light Rain Showers Polar Twilight'},
    {'id': 'heavyrainshowers_day', 'name': 'Heavy Rain Showers Day'},
    {'id': 'heavyrainshowers_night', 'name': 'Heavy Rain Showers Night'},
    {'id': 'heavyrainshowers_polartwilight', 'name': 'Heavy Rain Showers Polar Twilight'},
    {'id': 'lightsleetshowers_day', 'name': 'Light Sleet Showers Day'},
    {'id': 'lightsleetshowers_night', 'name': 'Light Sleet Showers Night'},
    {'id': 'lightsleetshowers_polartwilight', 'name': 'Light Sleet Showers Polar Twilight'},
    {'id': 'heavysleetshowers_day', 'name': 'Heavy Sleet Showers Day'},
    {'id': 'heavysleetshowers_night', 'name': 'Heavy Sleet Showers Night'},
    {'id': 'heavysleetshowers_polartwilight', 'name': 'Heavy Sleet Showers Polar Twilight'},
    {'id': 'lightsnowshowers_day', 'name': 'Light Snow Showers Day'},
    {'id': 'lightsnowshowers_night', 'name': 'Light Snow Showers Night'},
    {'id': 'lightsnowshowers_polartwilight', 'name': 'Light Snow Showers Polar Twilight'},
    {'id': 'heavysnowshowers_day', 'name': 'Heavy Snow Showers Day'},
    {'id': 'heavysnowshowers_night', 'name': 'Heavy Snow Showers Night'},
    {'id': 'heavysnowshowers_polartwilight', 'name': 'Heavy Snow Showers Polar Twilight'},
    {'id': 'lightrain', 'name': 'Light Rain'}, {'id': 'lightsleet', 'name': 'Light Sleet'},
    {'id': 'heavysleet', 'name': 'Heavy Sleet'}, {'id': 'lightsnow', 'name': 'Light Snow'},
    {'id': 'heavysnow', 'name': 'Heavy Snow'}]

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

WEATHER_CONDITION_CHOICES = [(condition['id'], _(condition['name'])) for condition in WEATHER_CONDITIONS]

WEATHER_CONDITIONS_AS_DICT = {condition['id']: condition for condition in WEATHER_CONDITIONS}
