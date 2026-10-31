"""Age dependency ratios and the share aged 65 and over, UN via the World Bank. Writes geo_age_dependency_country_year."""

from geo.models import AgeDependencyCountryYear

from . import api

COLUMNS = {
    'SP.POP.DPND': 'total',
    'SP.POP.DPND.OL': 'old',
    'SP.POP.65UP.TO.ZS': 'over_65',
}


def run():
    return api.load_indicators(AgeDependencyCountryYear, COLUMNS)
