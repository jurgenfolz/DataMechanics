"""Total fertility rate, births per woman, World Bank indicator SP.DYN.TFRT.IN. Writes geo_fertility_country_year."""

from geo.models import FertilityCountryYear

from . import api

CODE = 'SP.DYN.TFRT.IN'


def run():
    return api.load_indicator(FertilityCountryYear, CODE)
