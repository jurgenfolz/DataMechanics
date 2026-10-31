"""Adult mortality: the probability of dying between 15 and 60 per 1,000, World Bank indicators SP.DYN.AMRT.MA and SP.DYN.AMRT.FE. Writes geo_adult_mortality_country_year."""

from geo.models import AdultMortalityCountryYear

from . import api

COLUMNS = {
    'SP.DYN.AMRT.MA': 'men',
    'SP.DYN.AMRT.FE': 'women',
}


def run():
    return api.load_indicators(AdultMortalityCountryYear, COLUMNS)
