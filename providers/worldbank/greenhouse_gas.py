"""Greenhouse gas emissions (all gases, land use excluded), EDGAR via the World Bank. Writes geo_greenhouse_gas_emissions_country_year.

The total comes in megatonnes of CO2 equivalent; it is stored in tonnes, like the CO2 table.
"""

from geo.models import GreenhouseGasCountryYear

from . import api

COLUMNS = {
    'EN.GHG.ALL.PC.CE.AR5': 'per_capita',
    'EN.GHG.ALL.MT.CE.AR5': 'total',
}


def run():
    return api.load_indicators(GreenhouseGasCountryYear, COLUMNS, scale={'total': 1e6})
