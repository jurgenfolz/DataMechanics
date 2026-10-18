"""GDP in current US dollars, World Bank indicator NY.GDP.MKTP.CD. Writes geo_gdp_country_year."""

from geo.models import GdpCountryYear

from . import api

CODE = 'NY.GDP.MKTP.CD'


def run():
    return api.load_indicator(GdpCountryYear, CODE)
