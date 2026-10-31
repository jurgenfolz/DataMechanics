"""Infant mortality rate, UN IGME via the World Bank. Writes geo_infant_mortality_country_year."""

from geo.models import InfantMortalityCountryYear

from . import api

CODE = 'SP.DYN.IMRT.IN'


def run():
    return api.load_indicator(InfantMortalityCountryYear, CODE)
