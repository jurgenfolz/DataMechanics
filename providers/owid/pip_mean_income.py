"""Mean income or consumption per day (World Bank Poverty and Inequality Platform), as published by Our World in Data. Writes geo_mean_income_country_year."""

from geo.models import MeanIncomeCountryYear

from . import grapher

# The chart shows several views; these options pick this one.
VIEW = 'indicator=mean&decile=nan&period=day&survey_comparability=no_spells'
CHARTS = {'incomes-across-distribution-wb': {'mean__ppp_version_2021__welfare_type_income_or_consumption__period_day__table_income_or_consumption_consolidated__survey_comparability_no_spells': 'value'}}


def run():
    return grapher.load_charts(MeanIncomeCountryYear, CHARTS, view=VIEW)
