from django.db import transaction
from django.db.models import Q
from uuid import UUID
from rest_framework import serializers

from .forecast_settings import ForecastPeriod, WeatherCondition, ForecastDataParameters
from .models import City, Forecast, CityForecast, DataValue


class CitySerializer(serializers.ModelSerializer):
    coordinates = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = ('id', 'name', 'coordinates', "slug")

    def get_coordinates(self, obj):
        return obj.coordinates


class ForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = Forecast
        fields = ["forecast_date", "effective_period"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get("request")

        return instance.get_geojson(request)


class CityForecastPostSerializer(serializers.Serializer):
    city = serializers.CharField()
    condition = serializers.CharField()
    data_values = serializers.DictField(
        child=serializers.JSONField(),
        required=False,
        default=dict,
    )

    def validate(self, attrs):
        city_ref = attrs.get("city")
        condition_ref = attrs.get("condition")
        data_values = attrs.get("data_values") or {}

        city_query = Q(name__iexact=city_ref) | Q(slug__iexact=city_ref)
        try:
            city_uuid = UUID(str(city_ref))
            city_query = city_query | Q(id=city_uuid)
        except (ValueError, TypeError):
            pass

        city_obj = City.objects.filter(city_query).first()

        if not city_obj:
            raise serializers.ValidationError({"city": f"Unknown city: {city_ref}"})

        condition_obj = WeatherCondition.objects.filter(
            Q(symbol__iexact=condition_ref) |
            Q(label__iexact=condition_ref) |
            Q(alias__iexact=condition_ref)
        ).first()

        if not condition_obj:
            raise serializers.ValidationError({"condition": f"Unknown weather condition: {condition_ref}"})

        normalized_data_values = []
        for parameter_key, value in data_values.items():
            parameter_obj = ForecastDataParameters.objects.filter(
                Q(parameter__iexact=parameter_key) |
                Q(name__iexact=parameter_key)
            ).first()

            if not parameter_obj:
                raise serializers.ValidationError(
                    {"data_values": f"Unknown parameter: {parameter_key}"}
                )

            if value is None or value == "":
                continue

            if parameter_obj.parameter_type == "numeric":
                try:
                    float(value)
                except (TypeError, ValueError):
                    raise serializers.ValidationError(
                        {
                            "data_values": (
                                f"Invalid numeric value for '{parameter_key}': {value}"
                            )
                        }
                    )

            normalized_data_values.append({
                "parameter": parameter_obj,
                "value": str(value),
            })

        attrs["city_obj"] = city_obj
        attrs["condition_obj"] = condition_obj
        attrs["resolved_data_values"] = normalized_data_values
        return attrs


class ForecastPostSerializer(serializers.Serializer):
    forecast_date = serializers.DateField()
    effective_time = serializers.TimeField(help_text="Forecast effective time, e.g. '06:00:00'")
    source = serializers.ChoiceField(
        choices=[choice[0] for choice in Forecast.FORECAST_SOURCE_CHOICES],
        required=False,
        default="local",
    )
    replace_existing = serializers.BooleanField(required=False, default=True)
    city_forecasts = CityForecastPostSerializer(many=True)

    def validate_city_forecasts(self, value):
        if not value:
            raise serializers.ValidationError("At least one city forecast is required.")

        seen = set()
        for city_forecast in value:
            city_id = str(city_forecast["city_obj"].id)
            if city_id in seen:
                raise serializers.ValidationError(
                    f"Duplicate city in payload: {city_forecast['city_obj'].name}"
                )
            seen.add(city_id)

        return value

    def validate(self, attrs):
        effective_time = attrs.get("effective_time")
        period_obj = ForecastPeriod.objects.filter(forecast_effective_time=effective_time).first()
        if not period_obj:
            raise serializers.ValidationError({"effective_time": f"No ForecastPeriod found for time {effective_time}"})
        attrs["effective_period"] = period_obj
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        city_forecasts = validated_data.pop("city_forecasts")
        replace_existing = validated_data.pop("replace_existing", True)
        effective_period = validated_data.pop("effective_period")

        existing_forecasts = Forecast.objects.filter(
            forecast_date=validated_data["forecast_date"],
            effective_period=effective_period,
        )

        if existing_forecasts.exists():
            if not replace_existing:
                raise serializers.ValidationError(
                    "Forecast already exists for this date and effective period. "
                    "Set replace_existing=true to overwrite it."
                )
            existing_forecasts.delete()

        forecast = Forecast.objects.create(
            forecast_date=validated_data["forecast_date"],
            effective_period=effective_period,
            source=validated_data.get("source", "local")
        )

        for city_forecast_data in city_forecasts:
            city_forecast = CityForecast.objects.create(
                parent=forecast,
                city=city_forecast_data["city_obj"],
                condition=city_forecast_data["condition_obj"],
            )

            data_values = [
                DataValue(
                    parent=city_forecast,
                    parameter=data_value["parameter"],
                    value=data_value["value"],
                )
                for data_value in city_forecast_data["resolved_data_values"]
            ]

            if data_values:
                DataValue.objects.bulk_create(data_values)

        return forecast
