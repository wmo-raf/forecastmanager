import json
from itertools import groupby

from django.shortcuts import render
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core import serializers

from forecastmanager.models import City, Forecast, ConditionCategory

# Create your views here.
def add_forecast(request):
    city_ls = City.objects.all()
    weather_condition_ls = ConditionCategory.objects.all()
    # data = serializers.serialize('json', city_ls)
    # print(data)

    return render(request, "forecastmanager/forecast.html", {
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
                        'wind_direction':row['wind_direction'],
                        'wind_speed':row['wind_speed'],
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
    forecast_data = Forecast.objects.filter(city_id=city_id, forecast_date__gte=start_date_param,  forecast_date__lte=end_date_param).values('city__name','forecast_date', 'max_temp', 'min_temp', 'wind_speed', 'wind_direction', 'condition__title')

    if city_id is not None:
        return JsonResponse(list(forecast_data), safe=False)

    else:
        return JsonResponse({'error': 'City ID not provided.'})