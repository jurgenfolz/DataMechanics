"""The metrics Politics mode shows on a country page, as tabs in this order.

Remove a slug to hide a metric in Politics mode; add one (from metrics/catalog.py) to show it.
Each group becomes a labelled row of tabs.
"""

GROUPS = [
    ('Economy', ['gdp-per-capita', 'gdp', 'gdp-growth', 'labour-productivity', 'inflation', 'unemployment',
                 'government-debt', 'government-spending', 'tax-revenue', 'trade', 'women-in-the-labour-force']),
    ('Demography', ['population', 'fertility-rate', 'median-age']),
    ('Health', ['life-expectancy', 'child-mortality', 'obesity', 'health-spending']),
    ('Education', ['schooling', 'literacy-rate', 'education-spending', 'scientific-articles']),
    ('Development', ['hdi', 'mean-income', 'extreme-poverty', 'income-inequality', 'top-income-share']),
    ('Governance', ['democracy', 'human-rights', 'military-spending']),
    ('Corruption', ['political-corruption', 'executive-corruption', 'public-sector-corruption', 'judicial-corruption',
                    'corruption-perceptions']),
    ('Environment', ['co2-emissions', 'electricity-mix', 'air-pollution']),
    ('Food', ['undernourishment', 'healthy-diet-unaffordable', 'meat-production']),
    ('Society', ['life-satisfaction', 'homicide-rate', 'gender-wage-gap', 'women-political-empowerment',
                 'women-in-parliament']),
]

# Better directions that hold in Politics mode only, by (metric slug, series field): how a change during a presidency
# reads. The metric page's maps keep these neutral, because between countries a value is no better for being higher
# (a bigger economy, more trade, more spending on health or schools, more papers from a bigger country, fewer hungry people in a smaller one) or lower (falling prices, deflation, are no good sign either).
BETTER = {
    ('inflation', 'value'): 'lower',
    ('gdp', 'value'): 'higher',
    ('trade', 'value'): 'higher',
    ('health-spending', 'value'): 'higher',
    ('education-spending', 'value'): 'higher',
    ('scientific-articles', 'value'): 'higher',
    ('undernourishment', 'value'): 'lower',
}


def better(metric, series):
    """Which direction is better for a series in Politics mode: 'higher', 'lower' or '' for neither."""
    return BETTER.get((metric.slug, series.field), series.better)
