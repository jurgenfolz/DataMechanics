"""Military expenditure, % of GDP (SIPRI), World Bank indicator MS.MIL.XPND.GD.ZS. Writes geo_military_spending_country_year."""

from geo.models import MilitarySpendingCountryYear

from . import api

CODE = 'MS.MIL.XPND.GD.ZS'


def run():
    return api.load_indicator(MilitarySpendingCountryYear, CODE)
