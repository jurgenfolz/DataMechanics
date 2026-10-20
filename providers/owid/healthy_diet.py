"""The share of people who cannot afford a healthy diet (FAO and World Bank), as published by Our World in Data. Writes geo_healthy_diet_unaffordable_country_year."""

from geo.models import HealthyDietUnaffordableCountryYear

from . import grapher

CHARTS = {'share-healthy-diet-unaffordable': {'percent_of_the_population_who_cannot_afford_a_healthy_diet': 'value'}}


def run():
    return grapher.load_charts(HealthyDietUnaffordableCountryYear, CHARTS)
