"""Reads metric data from the database. Views and templates get everything through these functions.

Transformations stay small on purpose (see CLAUDE.md, Data design): reshaping and ranking only.
"""

from django.conf import settings
from django.db.models import Max, Min
from django.templatetags.static import static

from geo.models import Country, EtlLoad

from .formatting import format_value

WORLD = 'WLD'
# The map opens on the latest year that covers at least this share of the best-covered year.
MAP_YEAR_COVERAGE = 0.8


def flag_url(iso3, iso2, shape='4x3'):
    """The flag file for a country: '4x3' for rectangles, '1x1' for round avatars."""
    if iso3 == WORLD:
        return static('brand/world.svg')
    return f'{settings.MEDIA_URL}flags/{shape}/{iso2}.svg' if iso2 else ''


def latest_load(metric):
    return EtlLoad.objects.filter(table_name=metric.table).first()


def chart_data(metric, series):
    """Everything the metric page's charts draw for one series, in a compact column layout.

    `values` is {iso3: [value per year]}, aligned with `years` (None where missing).
    """
    rows = list(metric.model.objects.exclude(**{f'{series.field}__isnull': True})
                .values_list('country_id', 'year', series.field))
    years = list(range(min(r[1] for r in rows), max(r[1] for r in rows) + 1)) if rows else []
    values = {}
    for iso3, year, value in rows:
        values.setdefault(iso3, [None] * len(years))[year - years[0]] = _trim(value)

    countries = {
        c.iso3: {'name': metric.world_label if c.iso3 == WORLD else c.name, 'flag': flag_url(c.iso3, c.iso2)}
        for c in Country.objects.filter(iso3__in=values)
    }
    return {
        'field': series.field, 'label': series.label, 'unit': series.unit,
        'better': series.better, 'logScale': series.log_scale,
        'years': years,
        'mapYear': _map_year(values, years),
        'world': WORLD if WORLD in values else None,
        'countries': countries,
        'values': values,
    }


def map_shapes():
    """Country borders as GeoJSON for the map. Antarctica is left out: it has no data and takes space."""
    countries = Country.objects.filter(is_aggregate=False).exclude(geometry=None).exclude(iso3='ATA')
    return {
        'type': 'FeatureCollection',
        'features': [
            {'type': 'Feature', 'properties': {'iso3': c.iso3, 'name': c.name}, 'geometry': c.geometry}
            for c in countries
        ],
    }


def ranking(metric, series=None, limit=3):
    """The countries with the highest values in the latest well-covered year."""
    series = series or metric.series[0]
    year = latest_year(metric, series)
    if year is None:
        return None
    rows = (metric.model.objects.filter(year=year, country__is_aggregate=False)
            .exclude(**{f'{series.field}__isnull': True})
            .select_related('country')
            .order_by(f'-{series.field}'))
    world = metric.model.objects.filter(year=year, country_id=WORLD).values_list(series.field, flat=True).first()
    return {
        'year': year,
        'series': series,
        'count': rows.count(),
        'world': format_value(world, series.unit) if world is not None else None,
        'world_short': format_value(world, series.unit, compact=True) if world is not None else None,
        'rows': [_country_value(row.country, getattr(row, series.field), series) for row in rows[:limit]],
    }


def year_span(metric):
    """The first and last year with data, e.g. (1960, 2025)."""
    years = metric.model.objects.aggregate(first=Min('year'), last=Max('year'))
    return years['first'], years['last']


def latest_year(metric, series):
    counts = {}
    for year in (metric.model.objects.filter(country__is_aggregate=False)
                 .exclude(**{f'{series.field}__isnull': True}).values_list('year', flat=True)):
        counts[year] = counts.get(year, 0) + 1
    if not counts:
        return None
    best = max(counts.values())
    return max(year for year, count in counts.items() if count >= best * MAP_YEAR_COVERAGE)


def _map_year(by_country, years):
    counts = [sum(1 for iso3, row in by_country.items() if iso3 != WORLD and row[i] is not None)
              for i in range(len(years))]
    if not counts or not max(counts):
        return None
    best = max(counts)
    return max(year for year, count in zip(years, counts) if count >= best * MAP_YEAR_COVERAGE)


def _country_value(country, value, series):
    return {
        'iso3': country.iso3,
        'name': country.name,
        'flag': flag_url(country.iso3, country.iso2),
        'flag_round': flag_url(country.iso3, country.iso2, '1x1'),
        'value': format_value(value, series.unit),
        'value_short': format_value(value, series.unit, compact=True),
    }


def _trim(value):
    """Six significant digits: plenty for a chart, and it keeps the JSON small. Downloads keep full precision."""
    return float(f'{value:.6g}')
