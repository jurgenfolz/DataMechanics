"""Armed forces personnel per 1,000 people (IISS), World Bank indicator MS.MIL.TOTL.P1. Writes geo_armed_forces_country_year."""

from geo.models import ArmedForcesCountryYear

from . import api

COLUMNS = {
    'MS.MIL.TOTL.P1': 'value',
}


def run():
    return api.load_indicators(ArmedForcesCountryYear, COLUMNS)
