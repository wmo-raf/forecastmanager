import json
from itertools import groupby

from django.shortcuts import render
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core import serializers
from rest_framework import viewsets

from forecastmanager.models import City, Forecast
from .serializers import CitySerializer, ForecastSerializer
from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
    
class CityAPIView(viewsets.ModelViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = [IsAuthenticated|ReadOnly]



class ForecastAPIView(viewsets.ModelViewSet):
    queryset = Forecast.objects.all()
    serializer_class = ForecastSerializer
    permission_classes = [IsAuthenticated|ReadOnly]
    lookup_field = 'id'
    

    def get_serializer(self, *args, **kwargs):
        # Override the get_serializer method to handle list input
        kwargs['context'] = self.get_serializer_context()
        if isinstance(kwargs.get('data', {}), list):
            # If the input data is a list, use the many=True flag
            kwargs['many'] = True
        return self.serializer_class(*args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        forecast_date = self.request.query_params.get('forecast_date')

        if forecast_date:
            queryset = queryset.filter(forecast_date = forecast_date)
    
        return queryset
    
  
    

# Create your views here.
def add_forecast(request):
    city_ls = City.objects.all()
    weather_condition_ls = Forecast._meta.get_field('condition').choices
    # data = serializers.serialize('json', city_ls)

    return render(request, "forecastmanager/create_forecast.html", {
        "city_ls": serializers.serialize('json', city_ls, fields = ('name', 'id')),
        "weather_condition_ls": json.dumps([list(t)[0] for t in weather_condition_ls])
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
                    # condtion = ConditionCategory.objects.get(title=row['condition'])
                    # Create or update the child object with the parent and the name from the second column

                    Forecast.objects.update_or_create(
                        forecast_date=row['forecast_date'],
                        city=city, 
                    defaults={
                        'max_temp':row['max_temp'],
                        'min_temp':row['min_temp'],
                        'condition':row['condition'],
                    })
                return JsonResponse({'success': True})

            except IntegrityError as e:
                return JsonResponse({'error': 'Please fill in all required fields'},  status=400,  safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method.'},  status=400,  safe=False)
    
def get_forecast(request):

    dates_ls = Forecast.objects.order_by('-forecast_date').values_list('forecast_date', flat=True).distinct()[:7]
    print(dates_ls)
    
    return render(request, "forecastmanager/load_forecast.html", {
        'forecast_dates': dates_ls
    })
