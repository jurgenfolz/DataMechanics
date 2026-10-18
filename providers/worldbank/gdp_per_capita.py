"""GDP per person in current US dollars, World Bank indicator NY.GDP.PCAP.CD. Writes geo_gdp_per_capita_country_year."""

from geo.models import GdpPerCapitaCountryYear

from . import api

CODE = 'NY.GDP.PCAP.CD'


def run():
    return api.load_indicator(GdpPerCapitaCountryYear, CODE)
