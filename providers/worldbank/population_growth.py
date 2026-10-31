"""Population growth, % a year, World Bank indicator SP.POP.GROW. Writes geo_population_growth_country_year."""

from geo.models import PopulationGrowthCountryYear

from . import api

COLUMNS = {
    'SP.POP.GROW': 'value',
}


def run():
    return api.load_indicators(PopulationGrowthCountryYear, COLUMNS)
