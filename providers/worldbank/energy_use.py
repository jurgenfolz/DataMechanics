"""Energy use per person, IEA via the World Bank. Writes geo_energy_use_country_year."""

from geo.models import EnergyUseCountryYear

from . import api

CODE = 'EG.USE.PCAP.KG.OE'


def run():
    return api.load_indicator(EnergyUseCountryYear, CODE)
