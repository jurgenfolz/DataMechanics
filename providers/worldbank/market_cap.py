"""Market capitalisation of listed domestic companies, % of GDP, World Bank indicator CM.MKT.LCAP.GD.ZS. Writes geo_market_cap_country_year."""

from geo.models import MarketCapCountryYear

from . import api

COLUMNS = {
    'CM.MKT.LCAP.GD.ZS': 'value',
}


def run():
    return api.load_indicators(MarketCapCountryYear, COLUMNS)
