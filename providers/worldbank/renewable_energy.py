"""Renewable share of final energy consumption, IEA and UN via the World Bank. Writes geo_renewable_energy_country_year."""

from geo.models import RenewableEnergyCountryYear

from . import api

CODE = 'EG.FEC.RNEW.ZS'


def run():
    return api.load_indicator(RenewableEnergyCountryYear, CODE)
