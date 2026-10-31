"""International tourist arrivals and tourism receipts as % of exports (UN Tourism), World Bank indicators ST.INT.ARVL and ST.INT.RCPT.XP.ZS. Writes geo_tourism_country_year."""

from geo.models import TourismCountryYear

from . import api

COLUMNS = {
    'ST.INT.ARVL': 'arrivals',
    'ST.INT.RCPT.XP.ZS': 'receipts',
}


def run():
    return api.load_indicators(TourismCountryYear, COLUMNS)
