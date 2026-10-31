"""Cereal yield, kilograms per hectare, World Bank indicator AG.YLD.CREL.KG. Writes geo_cereal_yield_country_year."""

from geo.models import CerealYieldCountryYear

from . import api

COLUMNS = {
    'AG.YLD.CREL.KG': 'value',
}


def run():
    return api.load_indicators(CerealYieldCountryYear, COLUMNS)
