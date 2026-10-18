import csv

from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_control

from . import queries, search
from .catalog import BY_SLUG, CATEGORIES, METRICS
from .formatting import UNITS


def _metric(slug):
    try:
        return BY_SLUG[slug]
    except KeyError:
        raise Http404('No such metric.') from None


def metric_list(request):
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    if category not in CATEGORIES:
        category = ''
    results = search.find(query, category)
    return render(request, 'metrics/metric_list.html', {
        'query': query,
        'category': category,
        'results': [{'metric': m, 'top': queries.ranking(m, limit=2)} for m in results],
    })


def metric_detail(request, slug):
    metric = _metric(slug)
    related = [m for m in METRICS if m.tags.category == metric.tags.category and m is not metric]
    return render(request, 'metrics/metric_detail.html', {
        'metric': metric,
        'load': queries.latest_load(metric),
        'top': queries.ranking(metric, limit=10),
        'related': related or [m for m in METRICS if m is not metric][:3],
        'config': {'slug': metric.slug, 'units': UNITS, 'defaultCountries': list(metric.default_countries)},
    })


@cache_control(public=True, max_age=3600)
def metric_data(request, slug):
    """One series of a metric as JSON: ?series=<field>, the first series by default."""
    metric = _metric(slug)
    series = next((s for s in metric.series if s.field == request.GET.get('series')), metric.series[0])
    return JsonResponse(queries.chart_data(metric, series))


@cache_control(public=True, max_age=86400)
def country_shapes(request):
    return JsonResponse(queries.map_shapes())


def metric_csv(request, slug):
    """Every row of the metric's table, with its source on each row so any extract stays cited."""
    metric = _metric(slug)
    load = queries.latest_load(metric)
    fields = [series.field for series in metric.series]
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="data-mechanics-{metric.slug}.csv"'

    writer = csv.writer(response)
    writer.writerow(['iso3', 'country', 'year', *fields, 'source', 'source_url', 'source_updated', 'fetched_at'])
    source = [load.source_name, load.source_url, load.source_updated, load.loaded_at.isoformat()] if load else [''] * 4
    rows = metric.model.objects.select_related('country').order_by('country__name', 'year')
    for row in rows.iterator(chunk_size=5000):
        writer.writerow([row.country_id, row.country.name, row.year, *(getattr(row, f) for f in fields), *source])
    return response
