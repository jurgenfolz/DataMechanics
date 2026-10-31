from functools import cache
from pathlib import Path

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import gettext
from django.views.decorators.cache import cache_control

from geo.models import EtlLoad, State
from metrics.catalog import BY_SLUG, CATEGORY_LABELS
from metrics.formatting import units
from metrics.queries import flag_url, latest_load

from . import comparison, compass, congress, crime, crime_series, queries
from .metrics import GROUPS
from .models import Administration, Party
from .offices import office_of


def _country(slug):
    country = queries.country_by_slug(slug)
    if country is None:
        raise Http404('No Politics data for this country.')
    return country


def _metric_and_series(request, crimes):
    """The metric and measure the page asks for: a catalog metric of GROUPS, or one of the country's kinds of crime."""
    slugs = [slug for _, slugs in GROUPS for slug in slugs]
    asked = request.GET.get('metric')
    metric = BY_SLUG[asked] if asked in slugs else next((c for c in crimes if c.slug == asked), BY_SLUG[slugs[0]])
    series = next((s for s in metric.series if s.field == request.GET.get('series')), metric.series[0])
    return metric, series


def _is_crime(metric):
    return isinstance(metric, crime_series.Crime)


def _load(metric):
    """What the source line cites: the catalog metric's last load, or a kind of crime's own source."""
    return crime_series.load(metric) if _is_crime(metric) else latest_load(metric)


def _licence(source):
    """The licence a source asks to be named with, as {name, url}; None for a catalog metric's or one that asks nothing."""
    licence = getattr(source, 'licence', None)
    return {'name': licence.name, 'url': licence.url} if licence else None


def _source_line(load, licence):
    """What the page's source line shows: the source, its update, the load's date and any licence to name."""
    return {'name': load.source_name, 'url': load.source_url, 'updated': load.source_updated,
            'fetched': date_format(load.loaded_at, 'SHORT_DATE_FORMAT'), 'licence': licence} if load else None


def _metric_url(metric):
    """The metric's own page, where every country compares; a kind of crime has none."""
    return '' if _is_crime(metric) else reverse('metrics:detail', args=[metric.slug])


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
    crimes = crime_series.metrics(country)
    metric, series = _metric_and_series(request, crimes)
    groups = [(key, CATEGORY_LABELS[key], [BY_SLUG[s] for s in slugs if s in BY_SLUG]) for key, slugs in GROUPS]
    tenures = queries.tenures(country.iso3)
    office = office_of(tenures)
    # The party compass, the seats in Congress and crime suspects, for the countries that have them, as tabs of their own.
    compass_data = compass.data(country) if compass.has_compass(country) else None
    congress_data = congress.data(country) if congress.has_seats(country) else None
    crime_data = crime.data(country) if crime.has_suspects(country) else None
    # Crime per year closes the categories, with suspects by nationality as its last tab.
    if crimes or crime_data:
        groups.append(('crime', gettext('Crime'), crimes))
    group = next(key for key, _, items in groups if metric.slug in {m.slug for m in items})
    houses = [house['key'] for house in congress_data['houses']] if congress_data else []
    tab = request.GET.get('tab')
    tab = tab if {'compass': compass_data, 'congress': congress_data, 'crime': crime_data}.get(tab) else 'metric'
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
        'crime': crime_data,
        'tab': tab,
        'house_key': house_key,
        'metric': metric,
        'series': series,
        'current': tenures[-1],
        'current_party': queries.party_info(tenures[-1].periods[-1].party),
        'load': _load(metric),
        'metric_url': _metric_url(metric),
        'licence': _licence(metric.source) if _is_crime(metric) else None,
        'is_crime': _is_crime(metric),
        'crime_about': crime_series.ABOUT.get(country.iso3, ''),
        'politics_load': EtlLoad.objects.filter(table_name=Administration._meta.db_table).first(),
        'politics_source_url': tenures[0].periods[0].source_url,
        'logo_credits': _logo_credits(country),
        'config': {
            'dataUrl': reverse('politics:data', args=[slug]),
            'dataVersion': _deploy_version(),
            'statesUrl': reverse('politics:states', args=[slug]),
            'eventsUrl': reverse('events:json'),
            'countryName': country.local_name,
            'flag': flag,
            'pageTitle': title,
            'subtitle': office.subtitle % {'name': country.local_name},
            'units': units(),
            'metrics': {m.slug: {'title': m.title, 'summary': m.summary, 'url': _metric_url(m), 'crime': _is_crime(m),
                                 'series': [{'field': s.field, 'label': s.tab_label} for s in m.series]}
                        for _, _, items in groups for m in items},
            'metric': metric.slug,
            'series': series.field,
            'compare': _compare(request),
            'compass': compass_data,
            'congress': congress_data,
            'crime': crime_data,
            'tab': tab,
            'house': house_key,
            # The titles of the compass's and the seats' images and videos.
            'compassTitle': gettext('%(name)s’s party positions') % {'name': country.local_name},
            'congressTitle': congress_data['parliament']['title'] if congress_data else '',
            'crimeTitle': crime.title(country),
        },
    })


@cache_control(public=True, max_age=3600)
def country_data(request, slug):
    """One series as JSON. ?from=&to= (years) limit the presidents' changes and rankings to those years.
    ?compare= names the group the country is measured against (politics.comparison.GROUPS), or 'none'.
    """
    country = _country(slug)
    metric, series = _metric_and_series(request, crime_series.metrics(country))
    compare = _compare(request)
    if _is_crime(metric):
        data = queries.chart_data(metric, series, country, _window(request), None,
                                  values=crime_series.values(metric, series, country))
        # The map by state under the chart, with what it needs to colour and label its values.
        by_state = crime_series.states(metric, series, country)
        source = metric.states_source or metric.source
        data['states'] = by_state and {**by_state, 'label': data['label'], 'unit': series.unit, 'better': data['better'],
                                       'logScale': series.log_scale,
                                       'source': _source_line(crime_series.load(metric, source), _licence(source))}
    else:
        data = queries.chart_data(metric, series, country, _window(request),
                                  None if compare == comparison.NONE else compare)
    data['source'] = _source_line(_load(metric), _licence(metric.source) if _is_crime(metric) else None)
    return JsonResponse(data)


@cache_control(public=True, max_age=86400)
def country_states(request, slug):
    """The borders of the country's states, as GeoJSON for the map of crime by state, named in the page's language."""
    features = [{'type': 'Feature', 'properties': {'code': state.code, 'name': state.local_name}, 'geometry': state.geometry}
                for state in State.objects.filter(country=_country(slug))]
    return JsonResponse({'type': 'FeatureCollection', 'features': features})


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
