"""Foreign direct investment, net inflows, % of GDP. Writes geo_fdi_inflows_country_year."""

from geo.models import FdiInflowsCountryYear

from . import api

CODE = 'BX.KLT.DINV.WD.GD.ZS'


def run():
    return api.load_indicator(FdiInflowsCountryYear, CODE)
