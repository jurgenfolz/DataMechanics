"""The V-Dem rule of law index, as published by Our World in Data. Writes geo_rule_of_law_country_year."""

from geo.models import RuleOfLawCountryYear

from . import grapher

CHARTS = {'rule-of-law-index': {'rule_of_law_vdem__estimate_best': 'value'}}


def run():
    return grapher.load_charts(RuleOfLawCountryYear, CHARTS)
