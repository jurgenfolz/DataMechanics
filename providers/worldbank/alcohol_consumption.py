"""Alcohol consumption per adult, WHO via the World Bank. Writes geo_alcohol_consumption_country_year."""

from geo.models import AlcoholConsumptionCountryYear

from . import api

CODE = 'SH.ALC.PCAP.LI'


def run():
    return api.load_indicator(AlcoholConsumptionCountryYear, CODE)
