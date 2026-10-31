"""Household final consumption, % of GDP, World Bank indicator NE.CON.PRVT.ZS. Writes geo_household_consumption_country_year."""

from geo.models import HouseholdConsumptionCountryYear

from . import api

COLUMNS = {
    'NE.CON.PRVT.ZS': 'value',
}


def run():
    return api.load_indicators(HouseholdConsumptionCountryYear, COLUMNS)
