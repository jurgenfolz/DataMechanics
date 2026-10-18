"""Share of people living on less than $3.00 a day (2021 PPP), World Bank indicator SI.POV.DDAY. Writes geo_poverty_country_year."""

from geo.models import PovertyCountryYear

from . import api

CODE = 'SI.POV.DDAY'


def run():
    return api.load_indicator(PovertyCountryYear, CODE)
