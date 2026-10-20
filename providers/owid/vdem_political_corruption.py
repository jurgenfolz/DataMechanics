"""The V-Dem political corruption index, as published by Our World in Data. Writes geo_political_corruption_country_year."""

from geo.models import PoliticalCorruptionCountryYear

from . import grapher

CHARTS = {'political-corruption-index': {'corruption_vdem__estimate_best': 'value'}}


def run():
    return grapher.load_charts(PoliticalCorruptionCountryYear, CHARTS)
