"""Vulnerable employment: own-account and family workers, % of employment, ILO modelled estimates. Writes geo_vulnerable_employment_country_year."""

from geo.models import VulnerableEmploymentCountryYear

from . import api

CODE = 'SL.EMP.VULN.ZS'


def run():
    return api.load_indicator(VulnerableEmploymentCountryYear, CODE)
