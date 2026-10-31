"""Trade (exports plus imports), % of GDP, World Bank indicator NE.TRD.GNFS.ZS. Writes geo_trade_country_year."""

from geo.models import TradeCountryYear

from . import api

CODE = 'NE.TRD.GNFS.ZS'
# Exports and imports in local currency, to drop the shares the World Bank rounded away (Venezuela's 0% from 1991 to 2011).
AMOUNTS = {CODE: ['NE.EXP.GNFS.CN', 'NE.IMP.GNFS.CN']}


def run():
    return api.load_indicators(TradeCountryYear, {CODE: 'value'}, amounts=AMOUNTS)
