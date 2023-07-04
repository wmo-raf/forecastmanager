from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import InlinePanel
from wagtail.contrib.forms.models import AbstractFormField
from wagtail.models import Page

# from forecastmanager.models import AbstractMailChimpPage, AbstractMailchimpIntegrationForm


class HomePage(Page):
    pass


