"""Air passengers carried, World Bank indicator IS.AIR.PSGR. Writes geo_air_passengers_country_year."""

from geo.models import AirPassengersCountryYear

from . import api

COLUMNS = {
    'IS.AIR.PSGR': 'value',
}


def run():
    return api.load_indicators(AirPassengersCountryYear, COLUMNS)
