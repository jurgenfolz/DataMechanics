"""Interest payments on government debt, % of revenue, World Bank indicator GC.XPN.INTP.RV.ZS. Writes geo_interest_payments_country_year."""

from geo.models import InterestPaymentsCountryYear

from . import api

CODE = 'GC.XPN.INTP.RV.ZS'


def run():
    return api.load_indicator(InterestPaymentsCountryYear, CODE)
