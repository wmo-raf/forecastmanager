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

- This is simply implemented by enabling the automated forecasts checkbox under Forecast Settings > Forecast Source, then choosing a forecast provider. Forecasts are refreshed automatically on a schedule. For each city they are stored hourly for the current day and at 3-hourly periods (00, 03, 06, 09, 12, 15, 18, 21) for the following days.
- Two providers are supported:
  - **yr.no (Meteorological Norway)** — `source` value `yr`.
  - **Open-Meteo** — `source` value `open_meteo`.
- Each provider exposes its own set of source fields (e.g. air temperature, humidity, wind speed, precipitation) which an admin maps onto local forecast parameters under the parameter-mapping settings.

**Manual pull:** automated forecasts refresh on a schedule, but you can trigger an extra pull on demand. When automation is enabled, a **Pull forecasts now** button appears on the Forecasts listing. The pull runs as a **background task** (it does not block the web request), so the button returns immediately and the forecasts appear on the listing once the worker finishes. If a pull is already queued or running, clicking again won't start a second one. (If auto-publish is off, the pulled forecasts are saved as drafts for review.) The same run is available from the command line via `python manage.py generate_auto_forecast`.

> **Background worker required.** The manual pull (and any other background task) is executed by django-background-tasks, which needs a worker process running alongside the web server:
> ```bash
> python manage.py process_tasks
> ```
> Without this worker, clicking *Pull forecasts now* will queue the job but it will not execute until the worker runs. Run it as a long-lived process (e.g. a separate container, systemd service, or supervisor program) in production.

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

## Adding Cities

Cities (the locations forecasts are attached to) can be added in three ways:

1. **Manually** via the Cities snippet in the Wagtail admin.
2. **CSV upload** — Cities listing > *Import Cities*, then upload a CSV with city name, latitude, and longitude columns.
3. **Import from GeoNames** — Cities listing > *Import from GeoNames* (see below).

### Importing from GeoNames

This pulls cities from the free [GeoNames](https://www.geonames.org/) web service for a given country, so you don't have to assemble a CSV by hand. It is available both from the Wagtail admin and as a management command.

#### One-time setup

1. Create a free account at [geonames.org](https://www.geonames.org/login).
2. **Enable web services on the account.** This is the step that is easy to miss: after registering, log in, open your [account page](https://www.geonames.org/manageaccount), and click **"Click here to enable"** under *Free Web Services*. Until this is done, every request is rejected (see Troubleshooting). Activation can take up to an hour.
3. In the Wagtail admin, go to **Forecast Settings > Other Settings > GeoNames username** and save your account **username** (not the email address).

#### How the list is kept small

A single country can have tens of thousands of GeoNames entries, but most are not cities — they are rivers, mountains, roads, parks, and farms. The import reduces this in two layers:

1. **Filter by feature class.** Only GeoNames feature class **P** (populated places) is considered, which removes the non-settlement records.
2. **Select with an *admin seats + fill by population* strategy**, capped at a maximum:
   - Always include administrative seats — `PPLC` (national capital), `PPLA` (regional/first-order capitals), and `PPLA2` (district/second-order seats) — ordered by rank, so every administrative centre is covered even if it has a small population.
   - Fill the remaining slots with the highest-population populated places not already chosen, up to the configured maximum.

This guarantees both administrative coverage and a manageable list. The default cap is **200** and is adjustable per import.

Relevant GeoNames feature codes (full list at [geonames.org/export/codes.html](https://www.geonames.org/export/codes.html)):

| Code | Meaning |
| --- | --- |
| `PPLC` | National capital |
| `PPLA` | Seat of a first-order admin division (regional/provincial capital) |
| `PPLA2`–`PPLA5` | Seats of second- to fifth-order admin divisions (district/ward seats) |
| `PPL` | Generic populated place (towns, villages — selected by population) |

#### From the admin

1. Go to the **Cities** listing and click **Import from GeoNames**.
2. Enter the **ISO 3166 alpha-2 country code** (e.g. `MW` for Malawi, `KE` for Kenya).
3. Set the **maximum cities** (default 200).
4. Optionally tick **Update existing cities** to refresh the coordinates of cities that already exist (otherwise duplicates are skipped).
5. Click **Preview** to see exactly which cities will be imported (name, type, region, population, coordinates), then **Import** to save them.

#### From the command line

```bash
# Import (uses the username saved in Forecast Settings; default max 200)
python manage.py import_geonames_cities --country MW

# Preview only — list what would be imported, write nothing
python manage.py import_geonames_cities --country KE --max 150 --dry-run

# Update the locations of cities that already exist instead of skipping them
python manage.py import_geonames_cities --country MW --overwrite

# Override the configured username for a single run
python manage.py import_geonames_cities --country MW --username my_geonames_user
```

| Option | Description |
| --- | --- |
| `--country` | ISO 3166 alpha-2 country code (required). |
| `--max` | Maximum number of cities to import (default 200). |
| `--username` | GeoNames username; defaults to the one saved in Forecast Settings. |
| `--overwrite` | Update existing cities' locations instead of skipping them. |
| `--dry-run` | List the selected cities without writing to the database. |

#### Notes & troubleshooting

- City **names are unique**. An existing city is skipped unless you pass `--overwrite` (CLI) or tick *Update existing cities* (admin), in which case its location is updated.
- **`GeoNames error: user account not enabled to use the free webservice`** or a **401** response means web services have not been enabled on the account — complete step 2 of the setup above and wait for activation.
- **`GeoNames error: the daily limit ... has been exceeded`** means the account's free request quota is used up; it resets the next day.
- A GeoNames username must be set (in settings or via `--username`) or the import will refuse to run.

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
