# In your Django app's templatetags directory (e.g., myapp/templatetags/custom_filters.py)
from django import template

register = template.Library()


@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key)  # Use .get() to handle missing keys gracefully


@register.filter(name='get_elo')
def get_elo(profile):
    """
    Retrieves the elo_rating from a PlayerProfile instance.
    Returns None if the input is not a PlayerProfile or elo_rating is missing.
    """
    try:
        return int(profile.elo_rating)
    except AttributeError:
        return None  # Or a default value like "--"
