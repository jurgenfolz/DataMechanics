"""Tobacco use among people aged 15 and over (WHO), World Bank indicators SH.PRV.SMOK, .MA and .FE. Writes geo_smoking_country_year."""

from geo.models import SmokingCountryYear

from . import api

COLUMNS = {
    'SH.PRV.SMOK': 'total',
    'SH.PRV.SMOK.MA': 'men',
    'SH.PRV.SMOK.FE': 'women',
}


def run():
    return api.load_indicators(SmokingCountryYear, COLUMNS)
