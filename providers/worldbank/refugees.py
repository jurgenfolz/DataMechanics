"""Refugees by country of origin and of asylum, UNHCR via the World Bank. Writes geo_refugees_country_year."""

from geo.models import RefugeesCountryYear

from . import api

COLUMNS = {
    'SM.POP.RHCR.EO': 'from_country',
    'SM.POP.RHCR.EA': 'in_country',
}


def run():
    return api.load_indicators(RefugeesCountryYear, COLUMNS)
