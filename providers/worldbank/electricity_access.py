"""Access to electricity, % of the population. Writes geo_electricity_access_country_year."""

from geo.models import ElectricityAccessCountryYear

from . import api

CODE = 'EG.ELC.ACCS.ZS'


def run():
    return api.load_indicator(ElectricityAccessCountryYear, CODE)
