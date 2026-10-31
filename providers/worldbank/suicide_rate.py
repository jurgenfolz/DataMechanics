"""Suicide mortality rate, WHO Global Health Estimates via the World Bank. Writes geo_suicide_rate_country_year."""

from geo.models import SuicideRateCountryYear

from . import api

CODE = 'SH.STA.SUIC.P5'


def run():
    return api.load_indicator(SuicideRateCountryYear, CODE)
