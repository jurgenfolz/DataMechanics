"""Total reserves in months of imports. Writes geo_foreign_reserves_country_year."""

from geo.models import ForeignReservesCountryYear

from . import api

CODE = 'FI.RES.TOTL.MO'


def run():
    return api.load_indicator(ForeignReservesCountryYear, CODE)
