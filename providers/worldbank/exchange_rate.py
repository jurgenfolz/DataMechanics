"""Official exchange rate, local currency per US$, yearly average, World Bank indicator PA.NUS.FCRF. Writes geo_exchange_rate_country_year."""

from geo.models import ExchangeRateCountryYear

from . import api

COLUMNS = {
    'PA.NUS.FCRF': 'value',
}


def run():
    return api.load_indicators(ExchangeRateCountryYear, COLUMNS)
