"""Current account balance, % of GDP, IMF World Economic Outlook series BCA_NGDPD. Writes geo_current_account_country_year."""

from geo.models import CurrentAccountCountryYear

from . import datamapper


def run():
    return datamapper.load_series(CurrentAccountCountryYear, 'BCA_NGDPD', 'WEO')
