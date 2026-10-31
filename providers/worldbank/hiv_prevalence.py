"""HIV prevalence among people aged 15 to 49, UNAIDS via the World Bank. Writes geo_hiv_prevalence_country_year."""

from geo.models import HivPrevalenceCountryYear

from . import api

CODE = 'SH.DYN.AIDS.ZS'


def run():
    return api.load_indicator(HivPrevalenceCountryYear, CODE)
