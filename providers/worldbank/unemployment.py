"""Unemployment as % of the labour force (ILO modelled estimate), World Bank indicator SL.UEM.TOTL.ZS. Writes geo_unemployment_country_year."""

from geo.models import UnemploymentCountryYear

from . import api

CODE = 'SL.UEM.TOTL.ZS'


def run():
    return api.load_indicator(UnemploymentCountryYear, CODE)
