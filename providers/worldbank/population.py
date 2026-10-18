"""Population, births, deaths and net migration, from four World Bank indicators. Writes geo_population_country_year.

SP.POP.TOTL is the total population. SP.DYN.CBRT.IN and SP.DYN.CDRT.IN are births and deaths per 1,000 people.
SM.POP.NETM is net migration: immigrants minus emigrants.
"""

from geo.models import PopulationCountryYear

from . import api

COLUMNS = {
    'SP.POP.TOTL': 'population',
    'SP.DYN.CBRT.IN': 'birth_rate',
    'SP.DYN.CDRT.IN': 'death_rate',
    'SM.POP.NETM': 'net_migration',
}


def run():
    return api.load_indicators(PopulationCountryYear, COLUMNS)
