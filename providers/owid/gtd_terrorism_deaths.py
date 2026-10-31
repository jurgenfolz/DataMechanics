"""People killed in terrorist attacks, Global Terrorism Database via Our World in Data. Writes geo_terrorism_deaths_country_year."""

from geo.models import TerrorismDeathsCountryYear

from . import grapher

CHARTS = {
    'terrorism-deaths': {'total_killed': 'value'},
}


def run():
    return grapher.load_charts(TerrorismDeathsCountryYear, CHARTS)
