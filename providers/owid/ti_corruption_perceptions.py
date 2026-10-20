"""Transparency International's Corruption Perceptions Index, as published by Our World in Data. Writes geo_corruption_perceptions_country_year."""

from geo.models import CorruptionPerceptionsCountryYear

from . import grapher

CHARTS = {'ti-corruption-perception-index': {'cpi_score': 'value'}}


def run():
    return grapher.load_charts(CorruptionPerceptionsCountryYear, CHARTS)
