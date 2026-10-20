"""The V-Dem women's political empowerment index, as published by Our World in Data. Writes geo_women_political_empowerment_country_year."""

from geo.models import WomenPoliticalEmpowermentCountryYear

from . import grapher

CHARTS = {'women-political-empowerment-index': {'wom_emp_vdem__estimate_best': 'value'}}


def run():
    return grapher.load_charts(WomenPoliticalEmpowermentCountryYear, CHARTS)
