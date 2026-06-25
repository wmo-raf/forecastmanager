# Developer Guide: Adding City Forecasts to ClimWeb

This guide explains three ways to add city forecast data to ClimWeb, and how to retrieve forecasts via the read API (see [Retrieving Forecast Data](#retrieving-forecast-data-read-api)). For a more hands-on guide visit the [Forecast Manager Guide](https://climweb.readthedocs.io/en/latest/_docs/Manage-City-Forecasts.html):

---

## 1. Using the API

### Endpoint
- **POST** `/api/forecasts/post`

### Authentication
- Requires Token.
- Obtain a token via **POST** to `/api/token/` (TokenAuthentication) with payload 
```json
{
    "username":"your_username",
    "password":"your_password"
}
```

- Add header: `Authorization: Token <token>`

### Payload Example
```
{
  "forecast_date": "2026-03-11",
  "effective_time": "06:00:00",
  "source": "local",
  "replace_existing": true,
  "city_forecasts": [
    {
      "city": "nairobi",
      "condition": "Partly Cloudy",
      "data_values": {
        "max_temp": 28.5,
        "min_temp": 18.2,
        "humidity": 64
      }
    }
  ]
}
```

### Example Python Script
```python
import requests
API_URL = "http://<domain_name>/api/forecasts/post"
TOKEN = "your_token_here"
payload = { ... }
headers = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}
response = requests.post(API_URL, json=payload, headers=headers)
print(response.status_code)
print(response.json())
```

---

## 2. Automated City Forecast from Meteorological Providers

- This is simply implemented by enabling the automated forecasts checkbox under Forecast Settings > Forecast Source, then choosing a forecast provider. The forecast is updated automatically every three hours and has a 1 hour time interval (24 readings in a day).
- Two providers are supported:
  - **yr.no (Meteorological Norway)** — `source` value `yr`.
  - **Open-Meteo** — `source` value `open_meteo`.
- Each provider exposes its own set of source fields (e.g. air temperature, humidity, wind speed, precipitation) which an admin maps onto local forecast parameters under the parameter-mapping settings.

To read more about the providers visit:
- [YR Location data forecast model](https://developer.yr.no/doc/locationforecast/datamodel/)
- Weather forecasts on Yr - [how they are made](https://hjelp.yr.no/hc/en-us/articles/360004008874-Weather-forecasts-on-Yr-how-are-they-made)
- [Open-Meteo API documentation](https://open-meteo.com/en/docs)

---

## 3. Manual CSV Upload

- Use the admin interface or dedicated upload page to upload city forecast data via CSV. Visit [guide here.](https://climweb.readthedocs.io/en/latest/_docs/Manage-City-Forecasts.html)
- Download the CSV template .
- Fill in city forecast data in the template.
- Upload the CSV file using the web interface (typically via a form).
- The system will parse, validate, and import the data.
- Optionally, set 'overwrite existing' if you want to replace previous forecasts.

---

## Retrieving Forecast Data (Read API)

All read endpoints serve **published** forecasts only (drafts are withheld until reviewed) and are publicly accessible — no token required.

| Method & Endpoint | Description |
| --- | --- |
| **GET** `/api/cities` | List cities. Optional `?name=` filter (case-insensitive contains). |
| **GET** `/api/forecasts` | All published forecasts as GeoJSON. Optional `?forecast_date=` and `?effective_period=` filters. |
| **GET** `/api/forecast_mobile` | Single nearest-city forecast in Met Norway timeseries format (see below). |
| **GET** `/api/forecast-settings` | Configured data parameters and effective periods. |
| **GET** `/api/weather-icons` | Available weather condition icons with full URLs. |
| **GET** `/api/forecast_template.csv` | Download the CSV upload template. |

### Mobile Forecast Endpoint

- **GET** `/api/forecast_mobile?lat=<lat>&lon=<lon>`

Returns the forecast for the city **nearest** to the supplied coordinates, structured like the [Met Norway location forecast](https://developer.yr.no/doc/locationforecast/datamodel/) model. The `lat`/`lon` query parameters are required and are matched to the closest stored city. Each timeseries step carries only:

- `time` — the forecast's effective datetime (UTC).
- `data.instant.details` — the city's forecast data values.
- `data.next_1_hours.summary.symbol_code` — the weather condition symbol.

The `meta` block reports whether the match was the `exact` city or the `nearest` one, plus the unit for each parameter.

#### Example Response
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [35.05, -15.04]
  },
  "properties": {
    "meta": {
      "updated_at": "2026-06-25T09:00:00Z",
      "city": "Lilongwe",
      "location_source": "nearest",
      "location_description": "Forecast for the nearest city (Lilongwe).",
      "units": {
        "air_temperature": "°C",
        "cloud_area_fraction": "%",
        "precipitation_amount": "mm",
        "wind_from_direction": "degrees",
        "wind_speed": "m/s"
      }
    },
    "timeseries": [
      {
        "time": "2026-06-25T06:00:00Z",
        "data": {
          "instant": {
            "details": {
              "air_temperature": 20.5,
              "wind_speed": 2.3
            }
          },
          "next_1_hours": {
            "summary": { "symbol_code": "clearsky_day" }
          }
        }
      }
    ]
  }
}
```

> **Note:** `lat` is treated as latitude and `lon` as longitude. The `units` and `symbol_code` values reflect how each parameter and weather condition is configured in the admin.

---

## Notes
- All methods require valid city and parameter references.
- For API and automated methods, ensure authentication is set up.
- For manual upload, follow the template format and check for errors after upload.
- All weather symbols used are from [yr.no](https://nrkno.github.io/yr-weather-symbols/)

---

For further details, see the [API documentation ](https://climweb.readthedocs.io/en/latest/_docs/Manage-City-Forecasts.html).
