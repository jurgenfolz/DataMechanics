"""General government primary balance (% of GDP), IMF Fiscal Monitor series GGXONLB_G01_GDP_PT.
Writes geo_primary_balance_country_year.
"""

from geo.models import PrimaryBalanceCountryYear

from . import datamapper


def run():
    return datamapper.load_series(PrimaryBalanceCountryYear, 'GGXONLB_G01_GDP_PT', 'FM')
