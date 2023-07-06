from rest_framework import serializers, status
from .models import City, Forecast
from rest_framework.response import Response


class CitySerializer(serializers.ModelSerializer):

    coordinates = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = ('name', 'coordinates')

    def get_coordinates(self, obj):
        # Implement the logic to compute the property value here

        return obj.coordinates
    

class ForecastSerializer(serializers.ModelSerializer):

    city_detail =  serializers.SerializerMethodField()
    # condition_display = serializers.SerializerMethodField()
    list_serializer_class = serializers.ListSerializer

    class Meta:
        model = Forecast
        fields =['id','forecast_date','max_temp','min_temp', 'city', 'city_detail', 'condition']


    @staticmethod
    def get_city_detail(obj):
        serializer = CitySerializer(obj.city)
        return serializer.data
    
    # def get_condition_display(self, obj):
    #         return obj.get_condition_display()
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)

        forecast_feature = {
            "type": "Feature",
            "properties": {
                'id': representation['id'],
                'city_name': representation['city_detail']['name'],
                'forecast_date': representation['forecast_date'],
                'max_temp': representation['max_temp'],
                'min_temp': representation['min_temp'],
                'condition':representation['condition'],
                'condition_icon': f'{representation["condition"]}.png',
            },
            "geometry": {
                "coordinates": representation['city_detail']['coordinates'],
                "type": "Point"
            }
        }

        return forecast_feature


    def create(self, validated_data):
        forecast, created =  Forecast.objects.update_or_create(
            forecast_date=validated_data['forecast_date'],
            city=validated_data['city'], 
            defaults={
                'min_temp': validated_data['min_temp'],
                'max_temp': validated_data['max_temp'],
                'condition': validated_data['condition'],
            }
        )

        return forecast
    
        
        
        
    
