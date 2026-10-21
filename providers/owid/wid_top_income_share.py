"""The income share of the richest 1%, before tax (World Inequality Database), as published by Our World in Data. Writes geo_top_income_share_country_year."""

from geo.models import TopIncomeShareCountryYear

from . import grapher

# The chart shows several views; these options pick this one.
VIEW = 'quantile=richest_1pct&welfare_type=before_tax'
CHARTS = {'incomes-of-the-richest': {'share__welfare_type_before_tax__quantile_richest_1pct__extrapolated_no': 'value'}}


def run():
    return grapher.load_charts(TopIncomeShareCountryYear, CHARTS, view=VIEW)
