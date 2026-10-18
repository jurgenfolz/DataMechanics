"""Consumer price inflation, % per year, World Bank indicator FP.CPI.TOTL.ZG. Writes geo_inflation_country_year."""

from geo.models import InflationCountryYear

from . import api

CODE = 'FP.CPI.TOTL.ZG'


def run():
    return api.load_indicator(InflationCountryYear, CODE)
