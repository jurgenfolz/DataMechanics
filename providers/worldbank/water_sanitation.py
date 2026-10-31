"""Drinking water and sanitation, WHO/UNICEF Joint Monitoring Programme via the World Bank. Writes geo_water_and_sanitation_country_year."""

from geo.models import WaterSanitationCountryYear

from . import api

COLUMNS = {
    'SH.H2O.SMDW.ZS': 'water_safe',
    'SH.H2O.BASW.ZS': 'water_basic',
    'SH.STA.SMSS.ZS': 'sanitation_safe',
    'SH.STA.BASS.ZS': 'sanitation_basic',
}


def run():
    return api.load_indicators(WaterSanitationCountryYear, COLUMNS)
