"""Total factor productivity at constant national prices (Penn World Table), via Our World in Data. Writes geo_total_factor_productivity_country_year."""

from geo.models import TotalFactorProductivityCountryYear

from . import grapher

CHARTS = {
    'total-factor-productivity': {'rtfpna': 'value'},
}


def run():
    return grapher.load_charts(TotalFactorProductivityCountryYear, CHARTS)
