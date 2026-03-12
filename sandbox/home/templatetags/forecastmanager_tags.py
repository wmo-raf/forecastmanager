from datetime import date
from django import template

register = template.Library()


@register.filter
def get_dict_item(d, k):
    """
    Return the value of a dictionary for a given key. If the key does not exist, return None.
    """
    return d.get(k, None)


@register.filter
def date_is_today(value):
    if hasattr(value, "date"):
        value = value.date()
    return value == date.today()