from itertools import groupby

from datetime import datetime, timedelta
from django.shortcuts import render

from forecastmanager.models import Forecast, DailyWeather

def list_forecasts(request):

    start_date_param = datetime.today()
    end_date_param = start_date_param + timedelta(days=6)
    forecast_data = Forecast.objects.filter(forecast_date__gte=start_date_param.date(),  forecast_date__lte=end_date_param.date(),effective_period__whole_day = True )\
            .order_by('forecast_date')\
            .values('id','city__name','forecast_date', 'data_value', 'condition', 'effective_period', 'effective_period__whole_day', 'effective_period__forecast_effective_time')

    # sort the data by city
    data_sorted = sorted(forecast_data, key=lambda x: x['forecast_date'])
    # group the data by city
    grouped_forecast = {}
    for dates, group in groupby(data_sorted, lambda x: x['forecast_date']):
            dates_data = {'dates':dates, 'forecast_items': list(group)}

            # for item in  sorted(city_data['forecast_items'], key=lambda x: x['forecast_date']):
                # date_obj = datetime.strptime( item['forecast_date'], '%Y-%m-%d').date()
                # item['forecast_date'] =item['forecast_date']

            grouped_forecast[dates_data['dates']]  = dates_data['forecast_items']
            
    cities = list(set([d['city__name'] for d in data_sorted]))
    dates = list(set([d['forecast_date'] for d in data_sorted]))    
    
    return render(request, "integration/forecasts_include.html", {
        "forecasts":grouped_forecast,
        "cities":cities,
        "dates":sorted(dates)
    })

def daily_weather(request):
     
    report = DailyWeather.objects.all().order_by('issued_on').first()
     
    return render(request, "integration/dailyweather_include.html", {
        "report":report
    })


def city_analysis(request, city_name):
     
     context = {
          'city_name':city_name
     }
     
     return render(request, "integration/city_analysis.html", context)