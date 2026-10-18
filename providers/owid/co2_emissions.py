"""CO2 emissions per person and in total, Global Carbon Budget via Our World in Data. Writes geo_co2_emissions_country_year.

Fossil fuels and industry only; land-use change is not included.
"""

from geo.models import Co2EmissionsCountryYear

from . import grapher

CHARTS = {
    'co-emissions-per-capita': {'emissions_total_per_capita': 'per_capita'},
    'annual-co2-emissions-per-country': {'emissions_total': 'total'},
}


def run():
    return grapher.load_charts(Co2EmissionsCountryYear, CHARTS)
