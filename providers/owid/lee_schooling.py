"""Average years of schooling of people aged 15 to 64 since 1870, Lee and Lee via Our World in Data. Writes geo_schooling_long_run_country_year."""

from geo.models import SchoolingLongRunCountryYear

from . import grapher

CHARTS = {
    'mean-years-of-schooling-long-run': {'mf_youth_and_adults__15_64_years__average_years_of_education': 'value'},
}


def run():
    return grapher.load_charts(SchoolingLongRunCountryYear, CHARTS)
