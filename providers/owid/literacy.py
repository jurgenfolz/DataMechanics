"""Literacy rates, historical and recent, as compiled by Our World in Data. Writes geo_literacy_country_year."""

from geo.models import LiteracyCountryYear

from . import grapher

CHARTS = {'cross-country-literacy-rates': {'literacy_rate': 'value'}}


def run():
    return grapher.load_charts(LiteracyCountryYear, CHARTS)
