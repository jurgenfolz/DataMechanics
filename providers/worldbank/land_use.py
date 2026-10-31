"""Agricultural land, % of land area, and arable land per person, World Bank indicators AG.LND.AGRI.ZS and AG.LND.ARBL.HA.PC. Writes geo_land_use_country_year."""

from geo.models import LandUseCountryYear

from . import api

COLUMNS = {
    'AG.LND.AGRI.ZS': 'agricultural',
    'AG.LND.ARBL.HA.PC': 'arable_per_person',
}


def run():
    return api.load_indicators(LandUseCountryYear, COLUMNS)
