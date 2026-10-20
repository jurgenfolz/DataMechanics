"""Air pollution, two World Bank indicators from IHME's Global Burden of Disease study: PM2.5 exposure and the share of
people above the WHO guideline. Writes geo_air_pollution_country_year."""

from geo.models import AirPollutionCountryYear

from . import api

COLUMNS = {
    'EN.ATM.PM25.MC.M3': 'pm25',
    'EN.ATM.PM25.MC.ZS': 'above_guideline',
}


def run():
    return api.load_indicators(AirPollutionCountryYear, COLUMNS)
