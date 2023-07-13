from django.contrib import admin
from .models import Forecast


class ForecastAdmin(admin.ModelAdmin):
    pass


admin.site.register(Forecast, ForecastAdmin)
