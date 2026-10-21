"""Government spending as a share of GDP (IMF, Public Finances in Modern History), as published by Our World in Data. Writes geo_government_spending_country_year."""

from geo.models import GovernmentSpendingCountryYear

from . import grapher

CHARTS = {'historical-gov-spending-gdp': {'expenditure': 'value'}}


def run():
    return grapher.load_charts(GovernmentSpendingCountryYear, CHARTS)
