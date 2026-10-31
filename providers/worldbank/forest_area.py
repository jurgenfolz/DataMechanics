"""Forest area, % of land, FAO via the World Bank. Writes geo_forest_area_country_year."""

from geo.models import ForestAreaCountryYear

from . import api

CODE = 'AG.LND.FRST.ZS'


def run():
    return api.load_indicator(ForestAreaCountryYear, CODE)
