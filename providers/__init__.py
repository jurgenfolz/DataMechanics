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
    'worldbank.inflation',
    'worldbank.gdp_growth',
    'worldbank.fertility',
    'worldbank.child_mortality',
    'worldbank.poverty',
    'worldbank.inequality',
    'worldbank.military_spending',
    'worldbank.health_spending',
    'worldbank.female_labour',
    'worldbank.homicide',
    'worldbank.tax_revenue',
    'worldbank.trade',
    'owid.co2_emissions',
    'owid.electricity_mix',
    'owid.life_satisfaction',
    'owid.median_age',
    'owid.obesity',
    'owid.vdem_human_rights',
    # Politics mode: parties first, administrations point at them.
    'curated.parties',
    'curated.administrations',
]
