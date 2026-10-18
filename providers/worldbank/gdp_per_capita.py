"""GDP per person, in current US dollars and at purchasing power parity. Writes geo_gdp_per_capita_country_year.

NY.GDP.PCAP.CD converts at market exchange rates; NY.GDP.PCAP.PP.CD adjusts for price differences between countries.
"""

from geo.models import GdpPerCapitaCountryYear

from . import api

COLUMNS = {
    'NY.GDP.PCAP.CD': 'value',
    'NY.GDP.PCAP.PP.CD': 'ppp',
}


def run():
    return api.load_indicators(GdpPerCapitaCountryYear, COLUMNS)
