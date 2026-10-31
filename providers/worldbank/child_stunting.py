"""Child stunting, UNICEF/WHO/World Bank modelled estimates. Writes geo_child_stunting_country_year."""

from geo.models import ChildStuntingCountryYear

from . import api

CODE = 'SH.STA.STNT.ME.ZS'


def run():
    return api.load_indicator(ChildStuntingCountryYear, CODE)
