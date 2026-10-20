"""The V-Dem public sector corruption index, as published by Our World in Data. Writes geo_public_sector_corruption_country_year."""

from geo.models import PublicSectorCorruptionCountryYear

from . import grapher

CHARTS = {'public-sector-corruption-index': {'corr_publsec_vdem__estimate_best': 'value'}}


def run():
    return grapher.load_charts(PublicSectorCorruptionCountryYear, CHARTS)
