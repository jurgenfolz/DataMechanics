"""Consumption-based CO2 emissions per person, Global Carbon Project via Our World in Data. Writes geo_consumption_co2_country_year."""

from geo.models import ConsumptionCo2CountryYear

from . import grapher

CHARTS = {'consumption-co2-per-capita': {'consumption_emissions_per_capita': 'value'}}


def run():
    return grapher.load_charts(ConsumptionCo2CountryYear, CHARTS)
