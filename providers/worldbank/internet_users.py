"""Internet users, mobile subscriptions and fixed broadband, ITU via the World Bank. Writes geo_internet_users_country_year."""

from geo.models import InternetUsersCountryYear

from . import api

COLUMNS = {
    'IT.NET.USER.ZS': 'internet',
    'IT.CEL.SETS.P2': 'mobile',
    'IT.NET.BBND.P2': 'broadband',
}


def run():
    return api.load_indicators(InternetUsersCountryYear, COLUMNS)
