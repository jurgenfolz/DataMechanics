from django.http import JsonResponse
from django.views.decorators.cache import cache_control

from .catalog import EVENTS


@cache_control(public=True, max_age=3600)
def events_json(request):
    """Every world event the charts can mark, in the page's language, oldest first."""
    return JsonResponse({'events': [event.as_json() for event in EVENTS]})
