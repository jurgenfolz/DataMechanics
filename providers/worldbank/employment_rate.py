"""Employment-to-population ratio and labour force participation, people aged 15 and over, ILO modelled estimates. Writes geo_employment_rate_country_year."""

from geo.models import EmploymentRateCountryYear

from . import api

COLUMNS = {
    'SL.EMP.TOTL.SP.ZS': 'employed',
    'SL.TLF.CACT.ZS': 'in_labour_force',
}


def run():
    return api.load_indicators(EmploymentRateCountryYear, COLUMNS)
