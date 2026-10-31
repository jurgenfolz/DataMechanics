"""Measles and DTP immunisation of one-year-olds, WHO and UNICEF via the World Bank. Writes geo_immunisation_country_year."""

from geo.models import ImmunisationCountryYear

from . import api

COLUMNS = {
    'SH.IMM.MEAS': 'measles',
    'SH.IMM.IDPT': 'dtp',
}


def run():
    return api.load_indicators(ImmunisationCountryYear, COLUMNS)
