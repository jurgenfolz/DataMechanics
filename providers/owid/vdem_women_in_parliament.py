"""The share of women in parliament, from V-Dem, as published by Our World in Data. Writes geo_women_in_parliament_country_year."""

from geo.models import WomenInParliamentCountryYear

from . import grapher

CHARTS = {'share-of-women-in-parliament': {'wom_parl_vdem__estimate_best': 'value'}}


def run():
    return grapher.load_charts(WomenInParliamentCountryYear, CHARTS)
