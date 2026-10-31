"""GNI per capita, Atlas method, current US$, World Bank indicator NY.GNP.PCAP.CD. Writes geo_gni_per_capita_country_year."""

from geo.models import GniPerCapitaCountryYear

from . import api

COLUMNS = {
    'NY.GNP.PCAP.CD': 'value',
}


def run():
    return api.load_indicators(GniPerCapitaCountryYear, COLUMNS)
