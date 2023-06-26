import json
from itertools import groupby

from django.shortcuts import render
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core import serializers
from datetime import datetime, timedelta
from itertools import groupby
from wagtailgeowidget.helpers import geosgeometry_str_to_struct

from forecastmanager.models import City, Forecast, ConditionCategory

# Create your views here.
def add_forecast(request):
    city_ls = City.objects.all()
    weather_condition_ls = ConditionCategory.objects.all()
    # data = serializers.serialize('json', city_ls)
    # print(data)

    return render(request, "forecastmanager/create_forecast.html", {
        "city_ls": serializers.serialize('json', city_ls, fields = ('name', 'id')),
        "weather_condition_ls":serializers.serialize('json',weather_condition_ls, fields = ('title', 'id'))
    })


@csrf_exempt
def save_data(request):
    if request.method == 'POST':
        data = json.loads(request.POST.get('data', None))
        if len(data) > 0:
            # Iterate through the data and create or update Parent and Child objects
            try:
                print(data)
                for row in data:
                    # Get the name of the parent from the first column
                    parent_name = row['city']
                    # Try to get an existing parent with the same name, or create a new one
                    city = City.objects.get(name=parent_name)
                    condtion = ConditionCategory.objects.get(title=row['condition'])
                    # Create or update the child object with the parent and the name from the second column

                    Forecast.objects.update_or_create(
                        forecast_date=row['forecast_date'],
                        city=city, 
                    defaults={
                        'max_temp':row['max_temp'],
                        'min_temp':row['min_temp'],
                        'condition':condtion,
                    })
                return JsonResponse({'success': True})

            except IntegrityError as e:
                return JsonResponse({'error': 'Please fill in all required fields'},  status=400,  safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method.'},  status=400,  safe=False)


def get_data(request):
    start_date_param = request.GET.get('start_date', None)
    end_date_param = request.GET.get('end_date', None)
    city_id = request.GET.get('city_id', None)
    forecast_data = Forecast.objects.filter(city_id=city_id, forecast_date__gte=start_date_param,  forecast_date__lte=end_date_param).values('city__name','forecast_date', 'max_temp', 'min_temp', 'condition__title')

    if city_id is not None:
        return JsonResponse(list(forecast_data), safe=False)

    else:
        return JsonResponse({'error': 'City ID not provided.'})
    
def get_forecast_by_daterange(request):
    forecast_data = Forecast.objects.order_by('-forecast_date')\
        .values('id', 'city__name', 'city__location', 'forecast_date', 'max_temp', 'min_temp', 'condition__title', 'condition__icon_image', 'condition__icon_image__file')[:7]

    # sort the data by date
    data_sorted = sorted(forecast_data, key=lambda x: x['forecast_date'])

    # group the data by date
    grouped_forecast = []
    for forecast_date, group in groupby(data_sorted, lambda x: x['forecast_date']):
        city_data = {
            'forecast_date': forecast_date.strftime('%a %d, %b').replace(' 0', ' '),
            'forecast_features': {}
        }

        forecast_features = []
        for forecast in list(group):
            location = geosgeometry_str_to_struct(str(forecast['city__location']))
            feature = {
                "type": "Feature",
                "properties": {
                    'id': forecast['id'],
                    'city_name': forecast['city__name'],
                    'forecast_date': forecast['forecast_date'].strftime('%a %d, %b').replace(' 0', ' '),
                    'max_temp': forecast['max_temp'],
                    'min_temp': forecast['min_temp'],
                    'media_path': f"media.png",
                    'condition_icon': forecast['condition__icon_image__file'],
                    'condition_desc': forecast['condition__title'],
                },
                "geometry": {
                    "coordinates": [
                        float(location['x']),
                        float(location['y']),
                    ],
                    "type": "Point"
                }
            }

            forecast_features.append(feature)

        city_data['forecast_features'] = {
            "type": "FeatureCollection",
            "features": forecast_features
        }

        grouped_forecast.append(city_data)

    return render(request, "forecastmanager/load_forecast.html", {
        'day_forecast': grouped_forecast

    })
