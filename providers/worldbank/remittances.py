"""Personal remittances received, % of GDP. Writes geo_remittances_country_year."""

from geo.models import RemittancesCountryYear

from . import api

CODE = 'BX.TRF.PWKR.DT.GD.ZS'


def run():
    return api.load_indicator(RemittancesCountryYear, CODE)
