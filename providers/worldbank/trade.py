"""Trade (exports plus imports), % of GDP, World Bank indicator NE.TRD.GNFS.ZS. Writes geo_trade_country_year."""

from geo.models import TradeCountryYear

from . import api

CODE = 'NE.TRD.GNFS.ZS'


def run():
    return api.load_indicator(TradeCountryYear, CODE)
