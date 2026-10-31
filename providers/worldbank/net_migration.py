"""Net migration: immigrants minus emigrants, World Bank indicator SM.POP.NETM. Writes geo_net_migration_country_year."""

from geo.models import NetMigrationCountryYear

from . import api

COLUMNS = {
    'SM.POP.NETM': 'value',
}


def run():
    return api.load_indicators(NetMigrationCountryYear, COLUMNS)
