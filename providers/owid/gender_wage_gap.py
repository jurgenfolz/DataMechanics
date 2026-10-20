"""The ILO's unadjusted gender wage gap, as published by Our World in Data. Writes geo_gender_wage_gap_country_year."""

from geo.models import GenderWageGapCountryYear

from . import grapher

CHARTS = {'gender-gap-in-average-wages-ilo': {'gender_wage_gap_by_occupation__classif1_occupation__skill_level__total': 'value'}}


def run():
    return grapher.load_charts(GenderWageGapCountryYear, CHARTS)
