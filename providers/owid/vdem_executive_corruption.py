"""The V-Dem executive corruption index, as published by Our World in Data. Writes geo_executive_corruption_country_year."""

from geo.models import ExecutiveCorruptionCountryYear

from . import grapher

CHARTS = {'executive-corruption-index': {'corr_exec_vdem__estimate_best': 'value'}}


def run():
    return grapher.load_charts(ExecutiveCorruptionCountryYear, CHARTS)
