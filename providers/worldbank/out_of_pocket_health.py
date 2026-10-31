"""Out-of-pocket share of health spending, WHO Global Health Expenditure Database via the World Bank. Writes geo_out_of_pocket_health_country_year."""

from geo.models import OutOfPocketHealthCountryYear

from . import api

CODE = 'SH.XPD.OOPC.CH.ZS'


def run():
    return api.load_indicator(OutOfPocketHealthCountryYear, CODE)
