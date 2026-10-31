"""Urban population, % of the total, UN via the World Bank. Writes geo_urban_population_country_year."""

from geo.models import UrbanPopulationCountryYear

from . import api

CODE = 'SP.URB.TOTL.IN.ZS'


def run():
    return api.load_indicator(UrbanPopulationCountryYear, CODE)
