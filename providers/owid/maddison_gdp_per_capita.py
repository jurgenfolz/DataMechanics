"""GDP per capita in 2011 international dollars, Maddison Project Database via Our World in Data. Writes geo_maddison_gdp_per_capita_country_year."""

from geo.models import MaddisonGdpPerCapitaCountryYear

from . import grapher

CHARTS = {
    'gdp-per-capita-maddison': {'gdp_per_capita': 'value'},
}


def run():
    return grapher.load_charts(MaddisonGdpPerCapitaCountryYear, CHARTS)
