"""Physicians and hospital beds per 1,000 people, WHO via the World Bank. Writes geo_doctors_and_beds_country_year."""

from geo.models import DoctorsBedsCountryYear

from . import api

COLUMNS = {
    'SH.MED.PHYS.ZS': 'physicians',
    'SH.MED.BEDS.ZS': 'beds',
}


def run():
    return api.load_indicators(DoctorsBedsCountryYear, COLUMNS)
