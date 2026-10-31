"""Gross capital formation, gross fixed capital formation and gross savings, % of GDP. Writes geo_savings_and_investment_country_year."""

from geo.models import SavingsInvestmentCountryYear

from . import api

COLUMNS = {
    'NE.GDI.TOTL.ZS': 'investment',
    'NE.GDI.FTOT.ZS': 'fixed',
    'NY.GNS.ICTR.ZS': 'savings',
}
# Investment in local currency, to drop the shares the World Bank rounded away (Ethiopia's 0% from 1981 to 2010).
AMOUNTS = {'NE.GDI.TOTL.ZS': ['NE.GDI.TOTL.CN'], 'NE.GDI.FTOT.ZS': ['NE.GDI.FTOT.CN']}


def run():
    return api.load_indicators(SavingsInvestmentCountryYear, COLUMNS, amounts=AMOUNTS)
