"""Patent applications by residents and non-residents (WIPO), World Bank indicators IP.PAT.RESD and IP.PAT.NRES. Writes geo_patents_country_year."""

from geo.models import PatentsCountryYear

from . import api

COLUMNS = {
    'IP.PAT.RESD': 'residents',
    'IP.PAT.NRES': 'non_residents',
}


def run():
    return api.load_indicators(PatentsCountryYear, COLUMNS)
