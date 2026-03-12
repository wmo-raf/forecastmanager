# Developer Guide: Adding City Forecasts to ClimWeb

This guide explains three ways to add city forecast data to ClimWeb:

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
API_URL = "http://localhost:8001/api/forecasts/post"
TOKEN = "your_token_here"
payload = { ... }
headers = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}
response = requests.post(API_URL, json=payload, headers=headers)
print(response.status_code)
print(response.json())
```

---

## 2. Automated City Forecast from Meteorological Providers (Meteorological Norway)

- This is simply implemented by enabling the automated forecasts checkbox under Forecast Settings > Forecast Source. This forecasts is updated automatically every three hours and has a 1 hour time interval (24 readings in a day)

To read more about Meteorological Norway location forecast visit:
- [YR Location data forecast model](https://developer.yr.no/doc/locationforecast/datamodel/)
- Weather forecasts on Yr - [how they are made](https://hjelp.yr.no/hc/en-us/articles/360004008874-Weather-forecasts-on-Yr-how-are-they-made)

---

## 3. Manual CSV Upload

- Use the admin interface or dedicated upload page to upload city forecast data via CSV. Visit [guide here.](https://climweb.readthedocs.io/en/latest/_docs/Manage-City-Forecasts.html)
- Download the CSV template .
- Fill in city forecast data in the template.
- Upload the CSV file using the web interface (typically via a form).
- The system will parse, validate, and import the data.
- Optionally, set 'overwrite existing' if you want to replace previous forecasts.

---

## Notes
- All methods require valid city and parameter references.
- For API and automated methods, ensure authentication is set up.
- For manual upload, follow the template format and check for errors after upload.

---

For further details, see the [API documentation ](https://climweb.readthedocs.io/en/latest/_docs/Manage-City-Forecasts.html).
