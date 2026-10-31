"""Food production index, 2014 to 2016 = 100, World Bank indicator AG.PRD.FOOD.XD. Writes geo_food_production_country_year."""

from geo.models import FoodProductionCountryYear

from . import api

COLUMNS = {
    'AG.PRD.FOOD.XD': 'value',
}


def run():
    return api.load_indicators(FoodProductionCountryYear, COLUMNS)
