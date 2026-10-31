"""Private debt (households and firms), % of GDP, IMF Global Debt Database series PVD_LS and HH_LS. Writes geo_private_debt_country_year."""

from geo.models import PrivateDebtCountryYear

from . import datamapper

COLUMNS = {
    'PVD_LS': 'total',
    'HH_LS': 'households',
}


def run():
    return datamapper.load_columns(PrivateDebtCountryYear, COLUMNS, 'GDD')
