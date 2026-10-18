"""Under-5 mortality per 1,000 live births, World Bank indicator SH.DYN.MORT. Writes geo_child_mortality_country_year."""

from geo.models import ChildMortalityCountryYear

from . import api

CODE = 'SH.DYN.MORT'


def run():
    return api.load_indicator(ChildMortalityCountryYear, CODE)
