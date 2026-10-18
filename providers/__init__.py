"""ETL: one folder per data provider, one module per table.

Each module has a run() function that downloads its source and replaces its table.
Run them with `python manage.py etl` (all, in this order) or `python manage.py etl worldbank.gdp`.
"""

# The country dimension loads first: every fact table points at it.
MODULES = [
    'naturalearth.countries',
    'worldbank.gdp',
    'worldbank.gdp_per_capita',
    'worldbank.life_expectancy',
    'worldbank.unemployment',
    'worldbank.population',
    'imf.government_debt',
    'undp.hdi',
    'undp.schooling',
    'owid.vdem_democracy',
]
