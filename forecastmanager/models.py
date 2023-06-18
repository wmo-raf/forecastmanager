import uuid
import json
from django.utils.functional import cached_property
from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _
from wagtailgeowidget.panels import LeafletPanel
from wagtailgeowidget.helpers import geosgeometry_str_to_struct
from wagtail.admin.panels import FieldPanel

# Create your models here.
class City(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_("Unique UUID. Auto generated on creation."),
    )
    name = models.CharField(verbose_name=_("City Name"), max_length=255, null=True, blank=False,unique=True)
    location = models.PointField(verbose_name=_("City Location (Lat, Lng)"))

    panels = [
        FieldPanel("name"),
        LeafletPanel("location"),
    ]

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")

    def __str__(self) -> str:
        return self.name

    @cached_property
    def point(self):
        return json.dumps(geosgeometry_str_to_struct(str(self.location)))

    @property
    def lat(self):
        return self.point['y']

    @property
    def lng(self):
        return self.point['x']
 

class ConditionCategory(models.Model):
    title = models.CharField(max_length=50, help_text=_("Weather Condition Title"), verbose_name=_("Weather Condtion Title"))
    short_name = models.CharField(max_length=50, help_text=_("Weather Condition Short Name (helpgul for yr.no weather api)"), verbose_name=_("Weather Condtion Short Name"), null=True, blank=True, editable=False)
    description = models.CharField(max_length=250, blank=True, null=True, verbose_name=_("Description"))
    icon_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=False,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("Icon image")
    )


    class Meta:
        verbose_name = _("Weather Condition Category")
        verbose_name_plural = _("Weather Condition Categories")

    
    def __str__(self):
        return self.title
        

    def save(self, *args, **kwargs):
        if not self.short_name:
            self.short_name = self.icon_image.file.name.split('/')[-1].split('.')[0]
        super(ConditionCategory, self).save(*args, **kwargs)


class Forecast(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name=_("City"))
    forecast_date = models.DateField( auto_now=False, auto_now_add=False, verbose_name=_("Forecasts Date"))
    max_temp = models.IntegerField(verbose_name=_("Maximum Temperature"), blank=True)
    min_temp = models.IntegerField(verbose_name=_("Minimum Temperaure"), blank=True)
    wind_direction = models.IntegerField(verbose_name=_("Wind Direction"), blank=True, null=True)
    wind_speed = models.IntegerField(verbose_name=_("Wind Speed"), blank=True, null=True)
    # condition = models.CharField(verbose_name=_("General Weather Condition", max_length=255, blank=True, help_text="E.g Light Showers", default="Light Showers")
    condition = models.ForeignKey(ConditionCategory, verbose_name=_("General Weather Condition"), on_delete=models.CASCADE, help_text=_("E.g Light Showers"), null=True)

    class Meta:
        verbose_name = _("Forecast")
        verbose_name_plural = _("Forecasts")
        unique_together = ('city', 'forecast_date')

    panels = [
        FieldPanel("city"),
        FieldPanel("forecast_date"),
        FieldPanel("min_temp"),
        FieldPanel("max_temp"),
        FieldPanel("wind_direction"),
        FieldPanel("wind_speed"),
        FieldPanel("condition"),
    ]

    # def __str__(self):
    #     return f"{self.city} - {self.forecast_date}" 

