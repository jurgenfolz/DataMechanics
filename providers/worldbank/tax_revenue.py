"""Tax revenue, % of GDP (IMF), World Bank indicator GC.TAX.TOTL.GD.ZS. Writes geo_tax_revenue_country_year."""

from geo.models import TaxRevenueCountryYear

from . import api

CODE = 'GC.TAX.TOTL.GD.ZS'


def run():
    return api.load_indicator(TaxRevenueCountryYear, CODE)
