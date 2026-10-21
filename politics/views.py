from functools import cache
from pathlib import Path

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.formats import date_format
from django.views.decorators.cache import cache_control

from geo.models import EtlLoad
from metrics.catalog import BY_SLUG, CATEGORY_LABELS
from metrics.formatting import units
from metrics.queries import flag_url, latest_load

from . import queries
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


def country_page(request, slug):
    country = _country(slug)
    metric, series = _metric_and_series(request)
    groups = [(key, CATEGORY_LABELS[key], [BY_SLUG[s] for s in slugs if s in BY_SLUG]) for key, slugs in GROUPS]
    group = next(key for key, _, items in groups if metric.slug in {m.slug for m in items})
    tenures = queries.tenures(country.iso3)
    office = office_of(tenures)
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
        },
    })


@cache_control(public=True, max_age=3600)
def country_data(request, slug):
    """One series as JSON. ?from=&to= (years) limit the presidents' changes and rankings to those years."""
    metric, series = _metric_and_series(request)
    data = queries.chart_data(metric, series, _country(slug), _window(request))
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
