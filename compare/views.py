"""The Compare section: two metrics for one country, on one line chart with two axes.

The page draws from the metric pages' own data (metrics:data), so it needs no table of its own.
"""

from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse

from metrics import queries
from metrics.catalog import CATEGORY_LABELS, METRICS
from metrics.formatting import units

# What the chart opens with when the address names nothing.
DEFAULT_COUNTRY = 'USA'
DEFAULT_LEFT = 'gdp-per-capita:ppp'
DEFAULT_RIGHT = 'life-expectancy'


def series_key(metric, index):
    """How the page and its address name a measure: the metric's slug, then its field unless it is the first one."""
    return metric.slug if index == 0 else f'{metric.slug}:{metric.series[index].field}'


def index(request):
    return render(request, 'compare/index.html', {
        'groups': _groups(),
        'config': {
            'units': units(),
            'defaults': {'country': DEFAULT_COUNTRY, 'left': DEFAULT_LEFT, 'right': DEFAULT_RIGHT},
            'metrics': {metric.slug: _about(metric) for metric in METRICS},
            'eventsUrl': reverse('events:json'),
        },
    })


def _groups():
    """The measures the selects offer, by category, both in the order of their names in the active language."""
    groups = {}
    for metric in METRICS:
        for i, series in enumerate(metric.series):
            label = f'{metric.title} · {series.tab_label}' if len(metric.series) > 1 else str(metric.title)
            groups.setdefault(metric.tags.category, []).append({'key': series_key(metric, i), 'label': label})
    return [
        {'label': CATEGORY_LABELS[category], 'options': sorted(options, key=lambda option: option['label'])}
        for category, options in sorted(groups.items(), key=lambda item: str(CATEGORY_LABELS[item[0]]))
    ]


def _about(metric):
    """What the page shows of a metric beside the chart: its name, its page, its data and the source line above the chart."""
    return {
        'title': str(metric.title),
        'summary': str(metric.summary),
        'url': reverse('metrics:detail', args=[metric.slug]),
        'dataUrl': reverse('metrics:data', args=[metric.slug]),
        'csvUrl': reverse('metrics:csv', args=[metric.slug]),
        # The metric pages' own source line, so both pages cite a load the same way.
        'source': render_to_string('metrics/_source.html', {'load': queries.latest_load(metric)}).strip(),
    }
