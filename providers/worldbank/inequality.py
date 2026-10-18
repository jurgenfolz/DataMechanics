"""Gini index, World Bank indicator SI.POV.GINI. Writes geo_inequality_country_year."""

from geo.models import InequalityCountryYear

from . import api

CODE = 'SI.POV.GINI'


def run():
    return api.load_indicator(InequalityCountryYear, CODE)
