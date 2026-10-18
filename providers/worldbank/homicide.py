"""Intentional homicides per 100,000 people (UNODC), World Bank indicator VC.IHR.PSRC.P5. Writes geo_homicide_country_year."""

from geo.models import HomicideCountryYear

from . import api

CODE = 'VC.IHR.PSRC.P5'


def run():
    return api.load_indicator(HomicideCountryYear, CODE)
