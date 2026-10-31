"""The metrics Politics mode shows on a country page, as tabs in this order.

Remove a slug to hide a metric in Politics mode; add one (from metrics/catalog.py) to show it.
Each group becomes a labelled row of tabs.
"""

GROUPS = [
    ('Economy', ['gdp-per-capita', 'gdp-per-capita-long-run', 'gdp', 'gdp-growth', 'gni-per-capita', 'labour-productivity',
                 'total-factor-productivity', 'inflation', 'unemployment', 'youth-unemployment', 'youth-neet',
                 'employment-rate', 'labour-force-participation', 'employment-by-sector', 'vulnerable-employment',
                 'working-hours', 'minimum-wage', 'government-debt', 'interest-payments', 'budget-balance', 'primary-balance',
                 'government-spending', 'tax-revenue', 'trade', 'export-structure', 'current-account', 'fdi-inflows',
                 'savings-and-investment', 'household-consumption', 'private-debt', 'market-cap', 'remittances',
                 'foreign-reserves', 'economic-structure', 'women-in-the-labour-force', 'tourism']),
    ('Demography', ['population', 'population-growth', 'fertility-rate', 'birth-and-death-rates', 'adolescent-fertility',
                    'median-age', 'age-dependency', 'net-migration', 'urban-population', 'refugees']),
    ('Health', ['life-expectancy', 'infant-mortality', 'child-mortality', 'adult-mortality', 'maternal-mortality',
                'immunisation', 'obesity', 'smoking', 'alcohol-consumption', 'suicide-rate', 'road-deaths', 'tuberculosis',
                'hiv-prevalence', 'health-spending', 'out-of-pocket-health', 'doctors-and-beds', 'water-and-sanitation']),
    ('Education', ['schooling', 'schooling-long-run', 'school-enrolment', 'pisa', 'literacy-rate', 'education-spending',
                   'rd-spending', 'scientific-articles', 'patents']),
    ('Development', ['hdi', 'mean-income', 'extreme-poverty', 'income-inequality', 'top-income-share',
                     'electricity-access']),
    ('Governance', ['democracy', 'voter-turnout', 'human-rights', 'rule-of-law', 'freedom-of-expression',
                    'governance-indicators', 'military-spending', 'armed-forces', 'arms-imports', 'conflict-deaths',
                    'terrorism-deaths']),
    ('Corruption', ['political-corruption', 'executive-corruption', 'public-sector-corruption', 'judicial-corruption',
                    'corruption-perceptions']),
    ('Environment', ['co2-emissions', 'greenhouse-gas-emissions', 'consumption-co2', 'temperature-anomaly',
                     'electricity-mix', 'renewable-energy', 'energy-use', 'electricity-consumption', 'fossil-fuel-production',
                     'forest-area', 'land-use', 'water-stress', 'air-pollution']),
    ('Food', ['undernourishment', 'calorie-supply', 'child-stunting', 'healthy-diet-unaffordable', 'meat-production',
              'cereal-yield', 'food-production']),
    ('Society', ['life-satisfaction', 'homicide-rate', 'prison-population', 'gender-wage-gap', 'women-political-empowerment',
                 'women-in-parliament', 'lgbt-rights', 'internet-users', 'telephones', 'air-passengers']),
]

# Better directions that hold in Politics mode only, by (metric slug, series field): how a change during a presidency
# reads. The metric page's maps keep these neutral, because between countries a value is no better for being higher
# (a bigger economy, more trade, more spending on health or schools, more papers from a bigger country) or lower (falling prices, deflation, are no good sign either).
# Government spending growing as a share of GDP reads as bad during a term; between countries, the size of a state is a
# choice, not a score.
# Between countries, tax havens would top foreign investment, one country's current account surplus is another's deficit, and a larger share of farms, factories or services is no score.
BETTER = {
    ('inflation', 'value'): 'lower',
    ('gdp', 'value'): 'higher',
    ('trade', 'value'): 'higher',
    ('health-spending', 'value'): 'higher',
    ('education-spending', 'value'): 'higher',
    ('scientific-articles', 'value'): 'higher',
    ('government-spending', 'value'): 'lower',
    ('rd-spending', 'value'): 'higher',
    ('employment-rate', 'employed'): 'higher',
    ('savings-and-investment', 'investment'): 'higher',
    ('foreign-reserves', 'value'): 'higher',
    ('fdi-inflows', 'value'): 'higher',
    ('current-account', 'value'): 'higher',
    ('economic-structure', 'agriculture'): 'higher',
    ('economic-structure', 'industry'): 'higher',
    ('economic-structure', 'services'): 'higher',
    ('gdp-per-capita-long-run', 'value'): 'higher',
    ('gni-per-capita', 'value'): 'higher',
    ('patents', 'residents'): 'higher',
    ('food-production', 'value'): 'higher',
    ('air-passengers', 'value'): 'higher',
    ('tourism', 'arrivals'): 'higher',
    ('savings-and-investment', 'fixed'): 'higher',
}


def better(metric, series):
    """Which direction is better for a series in Politics mode: 'higher', 'lower' or '' for neither."""
    return BETTER.get((metric.slug, series.field), series.better)
