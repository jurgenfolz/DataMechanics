"""The V-Dem judicial corruption score, as published by Our World in Data. Writes geo_judicial_corruption_country_year."""

from geo.models import JudicialCorruptionCountryYear

from . import grapher

CHARTS = {'judicial-corruption-score': {'corr_jud_vdem__estimate_best': 'value'}}


def run():
    return grapher.load_charts(JudicialCorruptionCountryYear, CHARTS)
