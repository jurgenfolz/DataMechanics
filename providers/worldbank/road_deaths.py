"""Road traffic deaths, WHO via the World Bank. Writes geo_road_deaths_country_year."""

from geo.models import RoadDeathsCountryYear

from . import api

CODE = 'SH.STA.TRAF.P5'


def run():
    return api.load_indicator(RoadDeathsCountryYear, CODE)
