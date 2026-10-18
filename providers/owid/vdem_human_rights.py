"""The V-Dem human rights (civil liberties) index, as published by Our World in Data. Writes geo_human_rights_country_year."""

from geo.models import HumanRightsCountryYear

from . import grapher

CHARTS = {'human-rights-index-vdem': {'civ_libs_vdem__estimate_best': 'value'}}


def run():
    return grapher.load_charts(HumanRightsCountryYear, CHARTS)
