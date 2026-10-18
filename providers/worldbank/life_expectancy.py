"""Life expectancy at birth, World Bank indicator SP.DYN.LE00.IN. Writes geo_life_expectancy_country_year."""

from geo.models import LifeExpectancyCountryYear

from . import api

CODE = 'SP.DYN.LE00.IN'


def run():
    return api.load_indicator(LifeExpectancyCountryYear, CODE)
