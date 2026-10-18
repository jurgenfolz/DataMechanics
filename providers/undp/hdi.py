"""Human Development Index, UNDP Human Development Report. Writes geo_hdi_country_year."""

from geo.models import HdiCountryYear
from providers.load import replace_table

from . import composite_indices


def run():
    rows = {key: {'value': fields['hdi']} for key, fields in composite_indices.read_columns(['hdi']).items()}
    return replace_table(HdiCountryYear, rows, composite_indices.SOURCE)
