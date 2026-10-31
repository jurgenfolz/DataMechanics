"""Fixed telephone lines and mobile subscriptions per 100 people, World Bank indicators IT.MLT.MAIN.P2 and IT.CEL.SETS.P2. Writes geo_telephones_country_year."""

from geo.models import TelephonesCountryYear

from . import api

COLUMNS = {
    'IT.MLT.MAIN.P2': 'fixed',
    'IT.CEL.SETS.P2': 'mobile',
}


def run():
    return api.load_indicators(TelephonesCountryYear, COLUMNS)
