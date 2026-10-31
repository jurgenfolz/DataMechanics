"""PISA mean scores in mathematics and reading (OECD), via Our World in Data. Writes geo_pisa_country_year."""

from geo.models import PisaCountryYear

from . import grapher

CHARTS = {
    'pisa-test-score-mean-performance-on-the-mathematics-scale': {'pisa_math_all_average': 'maths'},
    'pisa-test-score-mean-performance-on-the-reading-scale': {'pisa_reading_all_average': 'reading'},
}


def run():
    return grapher.load_charts(PisaCountryYear, CHARTS)
