"""Median age, UN World Population Prospects via Our World in Data. Writes geo_median_age_country_year.

The chart also carries the UN's projections to 2100; only the estimates column is loaded.
"""

from geo.models import MedianAgeCountryYear

from . import grapher

CHARTS = {'median-age': {'median_age__sex_all__age_all__variant_estimates': 'value'}}


def run():
    return grapher.load_charts(MedianAgeCountryYear, CHARTS)
