"""Self-reported life satisfaction (0 to 10), World Happiness Report via Our World in Data. Writes geo_life_satisfaction_country_year."""

from geo.models import LifeSatisfactionCountryYear

from . import grapher

CHARTS = {'happiness-cantril-ladder': {'cantril_ladder_score': 'value'}}


def run():
    return grapher.load_charts(LifeSatisfactionCountryYear, CHARTS)
