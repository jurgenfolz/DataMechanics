"""The number of undernourished people (FAO), as published by Our World in Data. Writes geo_undernourishment_country_year."""

from geo.models import UndernourishmentCountryYear

from . import grapher

CHARTS = {'number-undernourished': {'_2_1_1_number_of_undernourished_people__000000000024001__value__006132__millions': 'value'}}


def run():
    return grapher.load_charts(UndernourishmentCountryYear, CHARTS)
