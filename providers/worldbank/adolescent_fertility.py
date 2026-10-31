"""Adolescent fertility rate, UN World Population Prospects via the World Bank. Writes geo_adolescent_fertility_country_year."""

from geo.models import AdolescentFertilityCountryYear

from . import api

CODE = 'SP.ADO.TFRT'


def run():
    return api.load_indicator(AdolescentFertilityCountryYear, CODE)
