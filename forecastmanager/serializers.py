from rest_framework import serializers

from .models import City, Forecast
from .site_settings import ForecastSetting


class CitySerializer(serializers.ModelSerializer):
    coordinates = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = ('id', 'name', 'coordinates')

    def get_coordinates(self, obj):
        # Implement the logic to compute the property value here
        return obj.coordinates


class ForecastSerializer(serializers.ModelSerializer):
    city_detail = serializers.SerializerMethodField()
    list_serializer_class = serializers.ListSerializer
    effective_period = serializers.SerializerMethodField()

    class Meta:
        model = Forecast
        fields = ['id', "city", 'forecast_date', 'condition', "city_detail", "effective_period"]

    @staticmethod
    def get_city_detail(obj):
        serializer = CitySerializer(obj.city)
        return serializer.data

    def get_effective_period(self, instance):
        return {
            "label": instance.effective_period.label,
            "time": instance.effective_period.forecast_effective_time,
            "whole_day": instance.effective_period.whole_day
        }

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get("request")

        forecast_setting = ForecastSetting.for_request(request)
        forecast_parameter_values = forecast_setting.data_parameter_values

        data_value = instance.data_value
        parameter_values_data = {}

        for param in forecast_parameter_values:
            param_name = param.get("parameter")
            if data_value and isinstance(data_value, dict) and data_value.get(param_name):
                parameter_values_data[param_name] = data_value.get(param_name)

        forecast_feature = {
            "type": "Feature",
            "properties": {
                'id': representation['id'],
                'city_name': representation['city_detail']['name'],
                'city_id': representation['city_detail']['id'],
                'forecast_date': representation['forecast_date'],
                'effective_period': representation['effective_period'],
                'condition': representation['condition'],
                **parameter_values_data,
                'condition_icon': f'{representation["condition"]}.png',
            },
            "geometry": {
                "coordinates": representation['city_detail']['coordinates'],
                "type": "Point"
            }
        }

        return {k: v for k, v in forecast_feature.items() if v or v == 0 or v is False}
