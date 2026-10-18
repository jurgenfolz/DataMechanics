from django.conf import settings
from django.urls import reverse

from geo.models import Country, EtlLoad
from metrics import search
from metrics.catalog import CATEGORIES


def site(request):
    return {
        'GITHUB_URL': settings.GITHUB_URL,
        'AUTHOR_LINKEDIN_URL': settings.AUTHOR_LINKEDIN_URL,
        'AUTHOR_GITHUB_URL': settings.AUTHOR_GITHUB_URL,
        'METRIC_CATEGORIES': CATEGORIES,
        'SEARCH_INDEX': search.index(),
        'SHAPES_URL': _shapes_url(),
    }


def _shapes_url():
    """The map shapes, versioned by the latest country load: browsers cache the file, and a reload busts it."""
    load = EtlLoad.objects.filter(table_name=Country._meta.db_table).values_list('loaded_at', flat=True).first()
    version = int(load.timestamp()) if load else 0
    return f"{reverse('metrics:shapes')}?v={version}"
