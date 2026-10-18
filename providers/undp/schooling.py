"""Mean and expected years of schooling, UNDP Human Development Report. Writes geo_schooling_country_year."""

from geo.models import SchoolingCountryYear
from providers.load import replace_table

from . import composite_indices


def run():
    rows = {
        key: {'mean_years': fields['mys'], 'expected_years': fields['eys']}
        for key, fields in composite_indices.read_columns(['mys', 'eys']).items()
    }
    return replace_table(SchoolingCountryYear, rows, composite_indices.SOURCE)
