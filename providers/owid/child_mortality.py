"""Deaths before age five per 1,000 live births since 1751 (Gapminder, UN IGME), via Our World in Data, which gives them per 100. Writes geo_child_mortality_country_year."""

from geo.models import ChildMortalityCountryYear

from . import grapher

CHARTS = {
    'child-mortality': {'child_mortality_rate': 'value'},
}


def run():
    return grapher.load_charts(ChildMortalityCountryYear, CHARTS, scale={'value': 10})
