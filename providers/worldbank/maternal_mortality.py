"""Maternal mortality ratio, UN agencies' modelled estimates via the World Bank. Writes geo_maternal_mortality_country_year."""

from geo.models import MaternalMortalityCountryYear

from . import api

CODE = 'SH.STA.MMRT'


def run():
    return api.load_indicator(MaternalMortalityCountryYear, CODE)
