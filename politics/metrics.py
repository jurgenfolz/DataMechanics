"""The metrics Politics mode shows on a country page, as tabs in this order.

Remove a slug to hide a metric in Politics mode; add one (from metrics/catalog.py) to show it.
Each group becomes a labelled row of tabs.
"""

GROUPS = [
    ('Economy', ['gdp-per-capita', 'gdp', 'gdp-growth', 'inflation', 'unemployment', 'government-debt',
                 'tax-revenue', 'trade', 'women-in-the-labour-force']),
    ('Demography', ['population', 'fertility-rate', 'median-age']),
    ('Health', ['life-expectancy', 'child-mortality', 'obesity', 'health-spending']),
    ('Education', ['schooling']),
    ('Development', ['hdi', 'extreme-poverty', 'income-inequality']),
    ('Governance', ['democracy', 'human-rights', 'military-spending']),
    ('Environment', ['co2-emissions', 'electricity-mix']),
    ('Society', ['life-satisfaction', 'homicide-rate']),
]
