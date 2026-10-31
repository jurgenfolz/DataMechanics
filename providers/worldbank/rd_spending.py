"""Research and development spending, % of GDP, UNESCO Institute for Statistics via the World Bank. Writes geo_rd_spending_country_year."""

from geo.models import RdSpendingCountryYear

from . import api

CODE = 'GB.XPD.RSDV.GD.ZS'


def run():
    return api.load_indicator(RdSpendingCountryYear, CODE)
