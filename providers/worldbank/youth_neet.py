"""Youth not in employment, education or training, % of those aged 15 to 24, World Bank indicator SL.UEM.NEET.ZS. Writes geo_youth_neet_country_year."""

from geo.models import YouthNeetCountryYear

from . import api

COLUMNS = {
    'SL.UEM.NEET.ZS': 'value',
}


def run():
    return api.load_indicators(YouthNeetCountryYear, COLUMNS)
