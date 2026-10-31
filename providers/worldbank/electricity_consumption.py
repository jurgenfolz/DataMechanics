"""Electricity consumption per person, IEA via the World Bank. Writes geo_electricity_consumption_country_year."""

from geo.models import ElectricityConsumptionCountryYear

from . import api

CODE = 'EG.USE.ELEC.KH.PC'


def run():
    return api.load_indicator(ElectricityConsumptionCountryYear, CODE)
