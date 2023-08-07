import pytz
from background_task import background
from background_task.models import Task
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.text import slugify
from wagtail.models import Site
import requests
import pandas as pd
import numpy as np

from wagtailgeowidget.helpers import geosgeometry_str_to_struct
from forecastmanager.models import City,Forecast
from forecastmanager.site_settings import ForecastSetting,ForecastPeriod


# Define the base URL for the Met Norway API
BASE_URL = "https://api.met.no/weatherapi/locationforecast/2.0/complete"
headers = {
  'User-Agent':'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Mobile Safari/537.36'
}

@background()
def generate_forecasts():
    tasks =  Task.objects.filter(verbose_name="generate_forecasts")
    print(f"No of tasks {len(tasks)}")

    cities_ls = list(City.objects.all().values())

    site = Site.objects.get(is_default_site=True)
    forecast_setting = ForecastSetting.for_site(site)

    # forecast_setting = ForecastSetting.objects.all().first()
    parameters = forecast_setting.data_parameter_values

    if forecast_setting.enable_auto_forecast:
        for city in cities_ls:

            location = geosgeometry_str_to_struct(str(city['location']))
            lat = location['y']
            lon = location['x']

            # Construct the API URL for this location
            url = f"{BASE_URL}?lat={lat}&lon={lon}"
            
            # Send a GET request to the API
            response = requests.get(url, headers=headers)
            
            # Check if the request was successful
            if response.status_code == 200:
                # Get the weather data from the response
                weather_data = response.json()
                data = weather_data['properties']['timeseries']

                df = pd.json_normalize(data)

                # convert the 'time' column to a datetime object and set it as the index
                df['time'] = pd.to_datetime(df['time'])
                df.set_index('time', inplace=True)


                # Define a function to extract the required values from a group
                def extract_values(group, params):
                    # Extract the minimum and maximum values of air temperature, wind speed, and wind direction
    
                    param_val = {}
                    for param in params:
                    
                        if param["parameter"] == 'air_temperature_max' or param["parameter"] =='air_temperature_min' or param["parameter"]  =='precipitation_amount':
                            param_val[f'{param["parameter"]}'] =round(group[f'data.next_6_hours.details.{param["parameter"]}'].mean(),1)
                            
                        else:
                            if f'data.instant.details.{param["parameter"]}' in group.columns:
                                param_val[f'{param["parameter"]}'] = round(group[f'data.instant.details.{param["parameter"]}'].mean(),1)

                            else:
                                param_val[f'{param["parameter"]}'] = None

                    param_val['condition'] = group['data.next_6_hours.summary.symbol_code'].iloc[0]

                    
                    return pd.Series(param_val)

                # Group the DataFrame by date and apply the extract_values() function to each group
                grouped = df.groupby(pd.Grouper(freq='D')).apply(extract_values, parameters)
                grouped = grouped.dropna(how="all")
                grouped = grouped.replace({np.nan: None})

                # Get the name of the parent from the first column
                parent_name = city['name']
                # Try to get an existing parent with the same name, or create a new one
                city = City.objects.get(name=parent_name)
                print("City:", parent_name )

                for index, row in grouped.iterrows():
                    time = index.to_pydatetime()
                    
                    # use update_or_create to update existing data
                    # and create new ones if the data does not exist
                    obj, created = Forecast.objects.update_or_create(
                        forecast_date=time,
                        city=city, 
                        defaults={
                            'condition':row['condition'].split('_')[0] if row['condition'] else row['condition'],
                            'effective_period':ForecastPeriod.objects.get(pk=1),
                            'data_value':row.to_dict()
                            }
                    )

        print("SUCCESSFULLY ADDED 7 DAY FORECAST")

    else:
        print("AUTOMATED FORECASTING DISABLED")