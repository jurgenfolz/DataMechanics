"""Real GDP growth, % per year, World Bank indicator NY.GDP.MKTP.KD.ZG. Writes geo_gdp_growth_country_year."""

from geo.models import GdpGrowthCountryYear

from . import api

CODE = 'NY.GDP.MKTP.KD.ZG'


def run():
    return api.load_indicator(GdpGrowthCountryYear, CODE)
