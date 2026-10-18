from django.conf import settings

from metrics import search
from metrics.catalog import CATEGORIES


def site(request):
    return {
        'GITHUB_URL': settings.GITHUB_URL,
        'AUTHOR_LINKEDIN_URL': settings.AUTHOR_LINKEDIN_URL,
        'AUTHOR_GITHUB_URL': settings.AUTHOR_GITHUB_URL,
        'METRIC_CATEGORIES': CATEGORIES,
        'SEARCH_INDEX': search.index(),
    }
