import logging
from django.core.management.base import BaseCommand

import pandas as pd
import json
import requests

from wagtailgeowidget.helpers import geosgeometry_str_to_struct
from forecastmanager.models import City,Forecast, ConditionCategory


# Define the base URL for the Met Norway API
BASE_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
headers = {
  'User-Agent':'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Mobile Safari/537.36'
}

logger = logging.getLogger(__name__)

default_options = () if not hasattr(BaseCommand, 'option_list') \
    else BaseCommand.option_list


class Command(BaseCommand):
    help = ('autotranslate all the message files that have been generated '
            'using the `makemessages` command.')

    def handle(self, *args, **options):

        # forecast_mode = list(IntegrationSettings.objects.all().values())
        # print("ATTEMPTING TO GENERATE 7 DAY FORECAST")
        # if forecast_mode[0]['enable_auto_forecast']:
           
        cities_ls = list(City.objects.all().values())

        for city in cities_ls:

            location = geosgeometry_str_to_struct(str(city['location']))
            lat = location['y']
            lon = location['x']

            # Construct the API URL for this location
            url = f"{BASE_URL}?lat={lat}&lon={lon}"

            print(url)
            
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
                def extract_values(group):
                    # Extract the minimum and maximum values of air temperature, wind speed, and wind direction
                    min_temp = group['data.instant.details.air_temperature'].min()
                    max_temp = group['data.instant.details.air_temperature'].max()
                    wind_speed = group['data.instant.details.wind_speed'].mean()
                    wind_dir = group['data.instant.details.wind_from_direction'].mean()
                    # Extract the value of next_12_hours summary
                    next_12_hours = group['data.next_12_hours.summary.symbol_code'].iloc[0]
                    # Create a dictionary of the extracted values
                    values = {'min_temp': min_temp, 'max_temp': max_temp, 'wind_speed': wind_speed,
                            'wind_dir': wind_dir, 
                            'next_12_hours': next_12_hours}
                    return pd.Series(values, index=['min_temp', 'max_temp', 
                                                    'wind_speed', 
                                                    'wind_dir', 
                                                    'next_12_hours'])

                # Group the DataFrame by date and apply the extract_values() function to each group
                grouped = df.groupby(pd.Grouper(freq='D')).apply(extract_values)
                grouped = grouped.dropna()

                # Get the name of the parent from the first column
                parent_name = city['name']
                # Try to get an existing parent with the same name, or create a new one
                city = City.objects.get(name=parent_name)
                
                for index, row in grouped.iterrows():
                    time = index.to_pydatetime()
                    min_temp = row['min_temp']
                    max_temp = row['max_temp']
                    wind_speed = row['wind_speed']
                    wind_dir = row['wind_dir']

                    # Create or update the child object with the parent and the name from the second column
                    # prioritize condition for the next 1 hour 
                    if 'next_1_hours' in row:
                        condition = ConditionCategory.objects.get(short_name=row['next_1_hours']) 
                    elif 'next_6_hours' in row:
                        condition = ConditionCategory.objects.get(short_name=row['next_6_hours']) 
                    else:
                        condition = ConditionCategory.objects.get(short_name=row['next_12_hours']) 

                    # use update_or_create to update existing data
                    # and create new ones if the data does not exist
                    obj, created = Forecast.objects.update_or_create(
                        forecast_date=time,
                        city=city, 
                        defaults={
                            'min_temp': min_temp,
                            'max_temp': max_temp,
                            'wind_speed': wind_speed,
                            'wind_direction': wind_dir,
                            'condition': condition
                        }
                    )

            else:
                # Handle errors
                print(f"Error fetching weather data for ({lat}, {lon}): {response.status_code}")


        # else:
        #     print("AUTOMATED FORECASTING DISABLED. Will try again in 3 hours")

            

