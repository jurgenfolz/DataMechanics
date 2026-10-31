"""The V-Dem freedom of expression index, as published by Our World in Data. Writes geo_freedom_of_expression_country_year."""

from geo.models import FreedomOfExpressionCountryYear

from . import grapher

CHARTS = {'freedom-of-expression-index': {'freeexpr_vdem__estimate_best': 'value'}}


def run():
    return grapher.load_charts(FreedomOfExpressionCountryYear, CHARTS)
