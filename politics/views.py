from functools import cache
from pathlib import Path

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import gettext
from django.views.decorators.cache import cache_control

from geo.models import EtlLoad
from metrics.catalog import BY_SLUG, CATEGORY_LABELS
from metrics.formatting import units
from metrics.queries import flag_url, latest_load

from . import comparison, compass, congress, queries
from .metrics import GROUPS
from .models import Administration, Party
from .offices import office_of


def _country(slug):
    country = queries.country_by_slug(slug)
    if country is None:
        raise Http404('No Politics data for this country.')
    return country


def _metric_and_series(request):
    slugs = [slug for _, slugs in GROUPS for slug in slugs]
    metric = BY_SLUG.get(request.GET.get('metric')) if request.GET.get('metric') in slugs else BY_SLUG[slugs[0]]
    series = next((s for s in metric.series if s.field == request.GET.get('series')), metric.series[0])
    return metric, series


def politics_index(request):
    return render(request, 'politics/index.html', {
        'cards': [queries.summary_card(item['country']) for item in queries.countries()],
    })


def _compare(request):
    """The comparison group the page asks for (?compare=), 'none' for no comparison, or the default: the world."""
    key = request.GET.get('compare')
    return key if key in comparison.GROUPS or key == comparison.NONE else comparison.DEFAULT


def country_page(request, slug):
    country = _country(slug)
    metric, series = _metric_and_series(request)
    groups = [(key, CATEGORY_LABELS[key], [BY_SLUG[s] for s in slugs if s in BY_SLUG]) for key, slugs in GROUPS]
    group = next(key for key, _, items in groups if metric.slug in {m.slug for m in items})
    tenures = queries.tenures(country.iso3)
    office = office_of(tenures)
    # The party compass and the seats in Congress, for the countries that have them, as the first tabs.
    compass_data = compass.data(country) if compass.has_compass(country) else None
    congress_data = congress.data(country) if congress.has_seats(country) else None
    houses = [house['key'] for house in congress_data['houses']] if congress_data else []
    tab = request.GET.get('tab')
    tab = tab if (tab == 'compass' and compass_data) or (tab == 'congress' and congress_data) else 'metric'
    house_key = request.GET.get('house') if request.GET.get('house') in houses else (houses[0] if houses else '')
    title = office.title % {'name': country.local_name}
    flag = flag_url(country.iso3, country.iso2, '1x1')
    return render(request, 'politics/country.html', {
        'country': country,
        'page_title': title,
        'lead': office.lead % {'year': tenures[0].start.year},
        'by_leader': office.by_leader,
        'flag': flag,
        'groups': groups,
        'group': group,
        'comparisons': [(key, group.label) for key, group in comparison.GROUPS.items()],
        'compare': _compare(request),
        'compass': compass_data,
        'congress': congress_data,
        'tab': tab,
        'house_key': house_key,
        'metric': metric,
        'series': series,
        'current': tenures[-1],
        'current_party': queries.party_info(tenures[-1].periods[-1].party),
        'load': latest_load(metric),
        'politics_load': EtlLoad.objects.filter(table_name=Administration._meta.db_table).first(),
        'politics_source_url': tenures[0].periods[0].source_url,
        'logo_credits': _logo_credits(country),
        'config': {
            'dataUrl': reverse('politics:data', args=[slug]),
            'dataVersion': _deploy_version(),
            'countryName': country.local_name,
            'flag': flag,
            'pageTitle': title,
            'subtitle': office.subtitle % {'name': country.local_name},
            'units': units(),
            'metrics': {m.slug: {'title': m.title, 'summary': m.summary, 'url': reverse('metrics:detail', args=[m.slug]),
                                 'series': [{'field': s.field, 'label': s.tab_label} for s in m.series]}
                        for _, _, items in groups for m in items},
            'metric': metric.slug,
            'series': series.field,
            'compare': _compare(request),
            'compass': compass_data,
            'congress': congress_data,
            'tab': tab,
            'house': house_key,
            # The titles of the compass's and the seats' images and videos.
            'compassTitle': gettext('%(name)s’s party positions') % {'name': country.local_name},
            'congressTitle': gettext('%(name)s’s Congress, party by party') % {'name': country.local_name},
        },
    })


@cache_control(public=True, max_age=3600)
def country_data(request, slug):
    """One series as JSON. ?from=&to= (years) limit the presidents' changes and rankings to those years.
    ?compare= names the group the country is measured against (politics.comparison.GROUPS), or 'none'.
    """
    metric, series = _metric_and_series(request)
    compare = _compare(request)
    data = queries.chart_data(metric, series, _country(slug), _window(request),
                              None if compare == comparison.NONE else compare)
    load = latest_load(metric)
    data['source'] = {'name': load.source_name, 'url': load.source_url, 'updated': load.source_updated,
                      'fetched': date_format(load.loaded_at, 'SHORT_DATE_FORMAT')} if load else None
    return JsonResponse(data)


@cache
def _deploy_version():
    """When the site was last deployed: every deploy collects the static files again, which rewrites their manifest.
    Browsers keep the data view's JSON for an hour, so its address carries this.
    A deploy that changes what the JSON holds is then never read from a copy made before it.
    """
    manifest = Path(settings.STATIC_ROOT) / 'staticfiles.json'
    return int(manifest.stat().st_mtime) if manifest.exists() else 0


def _window(request):
    try:
        first, last = int(request.GET['from']), int(request.GET['to'])
    except (KeyError, ValueError):
        return None
    return (first, last) if first <= last else None


def _logo_credits(country):
    """Logos that need attribution (anything not in the public domain)."""
    return Party.objects.filter(country=country).exclude(logo='').exclude(logo_licence='Public domain')
