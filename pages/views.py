from django.shortcuts import render

from blog.models import Post
from metrics import queries
from metrics.catalog import BY_SLUG, METRICS
from metrics.formatting import UNITS

# The spotlight cycles through these metrics, in this order.
SPOTLIGHT = ['life-expectancy', 'gdp-per-capita', 'co2-emissions', 'democracy', 'inflation', 'life-satisfaction',
             'government-debt', 'fertility-rate', 'hdi', 'electricity-mix', 'unemployment', 'population', 'gdp']
# Home page sections: (title, category to link to or '' for all metrics, up to four metric slugs).
SECTIONS = [
    ('Economy', 'Economy', ['gdp-per-capita', 'gdp-growth', 'inflation', 'government-debt']),
    ('People', '', ['population', 'fertility-rate', 'life-expectancy', 'child-mortality']),
    ('Environment', 'Environment', ['co2-emissions', 'electricity-mix']),
    ('Society and politics', '', ['democracy', 'human-rights', 'life-satisfaction', 'homicide-rate']),
]


def home(request):
    tops = {metric.slug: queries.ranking(metric, limit=3) for metric in METRICS}
    loads = {metric.slug: queries.latest_load(metric) for metric in METRICS}

    return render(request, 'pages/home.html', {
        'slides': [{'metric': BY_SLUG[slug], 'top': tops[slug], 'load': loads[slug]}
                   for slug in SPOTLIGHT if tops[slug]],
        # Newest data first: the metrics whose latest year is most recent lead the strip.
        'latest': sorted(({'metric': m, 'span': queries.year_span(m)} for m in METRICS if tops[m.slug]),
                         key=lambda item: (-item['span'][1], item['metric'].title)),
        'sections': [
            {'title': title, 'category': category,
             'items': [{'metric': BY_SLUG[slug], 'top': tops[slug]} for slug in slugs]}
            for title, category, slugs in SECTIONS
        ],
        'metric_count': len(METRICS),
        'posts': Post.published.prefetch_related('categories')[:3],
        'units': UNITS,
    })
