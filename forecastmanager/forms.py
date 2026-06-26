from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.forms import WagtailAdminModelForm

from forecastmanager.forecast_settings import (
    WeatherCondition,
    ForecastDataParameters
)


def parse_forecast_table(data):
    """
    Resolve a Handsontable ``{"fields": [...], "rows": [[...]]}`` payload into a
    list of ``{"city", "condition", "data_values"}`` dicts.

    Shared by the CSV/manual create flow and the grid editor. Raises
    ``forms.ValidationError`` on any unknown city/condition/parameter, missing
    required cell, or duplicate city.
    """
    from forecastmanager.models import City

    fields = data.get("fields") if data else None
    rows = data.get("rows") if data else None

    if not fields or not rows:
        raise forms.ValidationError(_("No data found in the table."))

    forecast_data = []
    added_cities = []

    for row in rows:
        data_dict = dict(zip(fields, row))

        city_name = data_dict.get("City")
        if not city_name:
            raise forms.ValidationError(_("City data is required."))

        city = City.objects.filter(name=city_name).first()
        if not city:
            raise forms.ValidationError(_("Unknown city found in table data: %(city)s") % {"city": city_name})

        if city.id in added_cities:
            raise forms.ValidationError(
                _("Duplicate city found in table data: %(city)s. Please remove the duplicate entry.")
                % {"city": city_name}
            )

        condition_name = data_dict.get("Condition")
        if not condition_name:
            raise forms.ValidationError(_("Condition data is required."))

        condition = WeatherCondition.objects.filter(Q(alias=condition_name) | Q(label=condition_name)).first()
        if not condition:
            raise forms.ValidationError(
                _("Unknown condition found in table data: %(condition)s") % {"condition": condition_name}
            )

        data_values = []
        for key, value in data_dict.items():
            if key in ("City", "Condition"):
                continue
            if value is not None and value != "":
                param = ForecastDataParameters.objects.filter(name=key).first()
                if not param:
                    raise forms.ValidationError(
                        _("Unknown parameter found in table data: %(param)s") % {"param": key}
                    )
                data_values.append({"parameter": param, "value": value})

        forecast_data.append({"city": city, "condition": condition, "data_values": data_values})
        added_cities.append(city.id)

    return forecast_data


class ForecastCreateForm(WagtailAdminModelForm):
    data = forms.JSONField(widget=forms.HiddenInput)
    replace_existing = forms.BooleanField(required=False, initial=True, label=_("Replace existing data if found"))

    def clean(self):
        cleaned_data = super().clean()
        forecast_date = cleaned_data.get("forecast_date")
        effective_period = cleaned_data.get("effective_period")
        replace_existing = cleaned_data.get("replace_existing")

        data = cleaned_data.get("data")

        fields = data.get("fields")
        rows = data.get("rows")

        if not fields or not rows:
            self.add_error(None, "No data found in the table.")
            return cleaned_data

        from forecastmanager.models import Forecast

        existing_forecasts = Forecast.objects.filter(
            forecast_date=forecast_date,
            effective_period=effective_period
        )

        if existing_forecasts.exists():
            # Check if user wants to overwrite
            if not replace_existing:
                self.add_error("forecast_date",
                               "Forecast data already exists for the given date and effective period. "
                               "To replace the existing data, check the 'Replace existing data if found' checkbox.")
                return cleaned_data
            else:
                cleaned_data["existing_forecasts"] = existing_forecasts
                self._validate_unique = False

        fields = data.get("fields")
        rows = data.get("rows")

        forecast_data = []
        added_cities = []

        for row in rows:
            data_dict = dict(zip(fields, row))

            # check city
            city = data_dict.get("City")
            if not city:
                self.add_error(None, "City data is required.")
                return cleaned_data

            from forecastmanager.models import City

            city = City.objects.filter(name=city).first()
            if not city:
                self.add_error(None, f"Unknown city found in table data: {city}")
                return cleaned_data

            if city.id in added_cities:
                self.add_error(None,
                               f"Duplicate city found in table data: {city}. Please remove the duplicate entry and try again.")
                return cleaned_data

            # check condition
            condition = data_dict.get("Condition")
            if not condition:
                self.add_error(None, "Condition data is required.")
                return cleaned_data

            condition = WeatherCondition.objects.filter(Q(alias=condition) | Q(label=condition)).first()
            if not condition:
                self.add_error(None, f"Unknown condition found in table data: {condition}")
                return cleaned_data

            city_data = {
                "city": city,
                "condition": condition,
                "data_values": []
            }

            params_data = {}
            for key, value in data_dict.items():
                if key not in ["City", "Condition"]:
                    params_data[key] = value

            # check parameters
            for param, value in params_data.items():
                if value is not None and value != "":
                    param = ForecastDataParameters.objects.filter(name=param).first()
                    if not param:
                        self.add_error(None, f"Unknown parameter found in table data: {param}")
                        return cleaned_data

                    city_data["data_values"].append({"parameter": param, "value": value})

            forecast_data.append(city_data)
            added_cities.append(city.id)

        cleaned_data["data"] = forecast_data
        return cleaned_data

    def save(self, commit=True):
        forecast = super().save(commit=False)

        forecast_data = self.cleaned_data.get("data")

        from forecastmanager.models import CityForecast, DataValue, Forecast

        # Forecaster-authored forecasts are published immediately.
        forecast.status = Forecast.STATUS_PUBLISHED

        if self.cleaned_data.get("existing_forecasts"):
            existing_forecasts = self.cleaned_data.get("existing_forecasts")
            existing_forecasts.delete()

        for city_data in forecast_data:
            city = city_data.get("city")
            condition = city_data.get("condition")
            data_values = city_data.get("data_values")

            city_forecast = CityForecast(
                city=city,
                condition=condition,
                data_source=CityForecast.DATA_SOURCE_MANUAL,
            )
            for data in data_values:
                city_forecast.data_values.add(DataValue(parameter=data.get("parameter"), value=data.get("value")))
            forecast.city_forecasts.add(city_forecast)

        if commit:
            forecast.save()

            for fn in hooks.get_hooks("after_forecast_add_from_form"):
                fn()

        return forecast


class CityLoaderForm(forms.Form):
    file = forms.FileField(label="File", required=True)
    overwrite_existing = forms.BooleanField(label="Overwrite existing data", required=False)
    data = forms.JSONField(widget=forms.HiddenInput)

    # only allow csv files
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].widget.attrs.update({'accept': '.csv'})

    def clean(self):
        cleaned_data = super().clean()
        data = cleaned_data.get("data")
        fields = data.get("fields")
        rows = data.get("rows")

        if not fields or not rows:
            self.add_error(None, "No data found in the table.")
            return cleaned_data

        fields = data.get("fields")
        rows = data.get("rows")

        cities = []
        added_cities = []
        for row in rows:
            data_dict = dict(zip(fields, row))
            city = data_dict.get("City")
            lat = data_dict.get("Latitude")
            lon = data_dict.get("Longitude")

            if city in added_cities:
                self.add_error(None,
                               f"Duplicate city found in table data: '{city}'. "
                               f"Please remove the duplicate entry and try again.")
                return cleaned_data

            added_cities.append(city)
            cities.append({"city": city, "lat": lat, "lon": lon})

        cleaned_data["data"] = cities

        return cleaned_data


class GeoNamesImportForm(forms.Form):
    country = forms.CharField(
        label=_("Country code"),
        max_length=2,
        min_length=2,
        help_text=_("ISO 3166 alpha-2 country code, e.g. MW for Malawi, KE for Kenya."),
    )
    max_cities = forms.IntegerField(
        label=_("Maximum cities"),
        min_value=1,
        max_value=1000,
        initial=200,
        help_text=_("Upper limit on how many cities to import (default 200)."),
    )
    overwrite_existing = forms.BooleanField(
        label=_("Update existing cities"),
        required=False,
        help_text=_("If a city with the same name exists, update its location instead of skipping it."),
    )

    def clean_country(self):
        return self.cleaned_data["country"].strip().upper()


class ForecastEditForm(WagtailAdminModelForm):
    pass
