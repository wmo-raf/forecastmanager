from rest_framework import serializers

from .models import City, Forecast


class CitySerializer(serializers.ModelSerializer):
    coordinates = serializers.SerializerMethodField()
    clean_name = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = ('id', 'name', 'coordinates', "clean_name")

    def get_coordinates(self, obj):
        return obj.coordinates

    def get_clean_name(self, obj):
        return obj.clean_name


class ForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = Forecast
        fields = ["forecast_date", "effective_period"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get("request")

        return instance.get_geojson(request)
