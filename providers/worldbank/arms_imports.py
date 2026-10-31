"""Arms imports, SIPRI trend-indicator values via the World Bank. Writes geo_arms_imports_country_year."""

from geo.models import ArmsImportsCountryYear

from . import api

CODE = 'MS.MIL.MPRT.KD'


def run():
    return api.load_indicator(ArmsImportsCountryYear, CODE)
