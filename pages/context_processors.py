from functools import cache
from pathlib import Path

from django.conf import settings
from django.urls import reverse, translate_url
from django.utils import translation

from geo.models import Country, EtlLoad
from metrics import search
from metrics.catalog import CATEGORIES, CATEGORY_LABELS


def site(request):
    return {
        'GITHUB_URL': settings.GITHUB_URL,
        'AUTHOR_LINKEDIN_URL': settings.AUTHOR_LINKEDIN_URL,
        'AUTHOR_GITHUB_URL': settings.AUTHOR_GITHUB_URL,
        # (key, label) pairs, in the order of the labels in the active language.
        'METRIC_CATEGORIES': sorted(((key, CATEGORY_LABELS[key]) for key in CATEGORIES), key=lambda item: str(item[1])),
        'SEARCH_INDEX': search.index(),
        'SHAPES_URL': _shapes_url(),
        'CATALOG_URL': f"{reverse('javascript-catalog')}?v={_catalog_version()}",
        'LANGUAGES_HERE': _languages_here(request),
    }


def _languages_here(request):
    """This page in every language: the switcher links to `url`, the head's hreflang links to `canonical`."""
    current = translation.get_language()
    return [
        {
            'code': code,
            'name': name,
            'current': code == current,
            'url': translate_url(request.get_full_path(), code),
            'canonical': request.build_absolute_uri(translate_url(request.path, code)),
        }
        for code, name in settings.LANGUAGES
    ]


@cache
def _catalog_version():
    """The JavaScript catalog's version: the time its translations were last compiled.
    Browsers keep the catalog for an hour, so a deploy that changes a text must change its address.
    Every deploy compiles the translations and restarts the site, so the version is read once per process.
    """
    files = [path for folder in settings.LOCALE_PATHS for path in Path(folder).glob('*/LC_MESSAGES/djangojs.mo')]
    return int(max((path.stat().st_mtime for path in files), default=0))


def _shapes_url():
    """The map shapes, versioned by the latest country load: browsers cache the file, and a reload busts it."""
    load = EtlLoad.objects.filter(table_name=Country._meta.db_table).values_list('loaded_at', flat=True).first()
    version = int(load.timestamp()) if load else 0
    return f"{reverse('metrics:shapes')}?v={version}"
