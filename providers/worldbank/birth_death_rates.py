"""Crude birth and death rates per 1,000 people, World Bank indicators SP.DYN.CBRT.IN and SP.DYN.CDRT.IN. Writes geo_birth_death_rates_country_year."""

from geo.models import BirthDeathRatesCountryYear

from . import api

COLUMNS = {
    'SP.DYN.CBRT.IN': 'births',
    'SP.DYN.CDRT.IN': 'deaths',
}


def run():
    return api.load_indicators(BirthDeathRatesCountryYear, COLUMNS)
