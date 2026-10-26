"""ETL: one folder per data provider, one module per table.

Each module has a run() function that downloads its source and replaces its table.
Run them with `python manage.py etl` (every module in MODULES, in this order) or `python manage.py etl worldbank.gdp`.

The conflicts' modules (CONFLICT_MODULES) are not part of a plain `etl` run, so the weekly refresh never touches them:
World War II is history, and its sources are pinned. They load only when named, as every deploy does.
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
    'imf.budget_balance',
    'imf.primary_balance',
    'worldbank.interest_payments',
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
    'owid.vdem_political_corruption',
    'owid.vdem_executive_corruption',
    'owid.vdem_public_sector_corruption',
    'owid.vdem_judicial_corruption',
    'owid.ti_corruption_perceptions',
    'owid.literacy',
    'owid.education_spending',
    'worldbank.scientific_articles',
    'owid.gender_wage_gap',
    'owid.vdem_women_empowerment',
    'owid.vdem_women_in_parliament',
    'worldbank.undernourishment',
    'owid.healthy_diet',
    'owid.fao_meat_production',
    'worldbank.air_pollution',
    'owid.wid_top_income_share',
    'owid.pip_mean_income',
    'owid.pwt_productivity',
    'owid.imf_government_spending',
    # Politics mode: parties first, administrations point at them.
    'curated.parties',
    'curated.administrations',
    'curated.party_profiles',
    'curated.party_positions',
    'curated.party_left_right',
    'camara.deputies',
    'senado.senators',
    'tse.elected',
    'abgeordnetenwatch.bundestag',
    'parlament_at.nationalrat',
    'parlament_at.bundesrat',
]

# World War II, in the conflicts database: the states first, every other table points at them.
CONFLICT_MODULES = [
    'curated.ww2_states',
    'curated.ww2_sides',
    'wikipedia.ww2_deaths',
    'curated.ww2_battles',
    'curated.ww2_events',
    'cshapes.ww2_borders',
]
