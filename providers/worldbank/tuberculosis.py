"""Tuberculosis incidence, WHO via the World Bank. Writes geo_tuberculosis_country_year."""

from geo.models import TuberculosisCountryYear

from . import api

CODE = 'SH.TBS.INCD'


def run():
    return api.load_indicator(TuberculosisCountryYear, CODE)
