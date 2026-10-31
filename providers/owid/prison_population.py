"""Prisoners per 100,000 people, World Prison Brief via Our World in Data. Writes geo_prison_population_country_year."""

from geo.models import PrisonPopulationCountryYear

from . import grapher

CHARTS = {
    'prison-population-rate': {'prison_population_rate': 'value'},
}


def run():
    return grapher.load_charts(PrisonPopulationCountryYear, CHARTS)
