"""Water stress, FAO AQUASTAT via the World Bank. Writes geo_water_stress_country_year."""

from geo.models import WaterStressCountryYear

from . import api

CODE = 'ER.H2O.FWST.ZS'


def run():
    return api.load_indicator(WaterStressCountryYear, CODE)
