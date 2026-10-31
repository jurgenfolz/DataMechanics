"""Employment by sector and self-employment, % of all employment (ILO modelled), World Bank indicators SL.*.EMPL.ZS and SL.EMP.SELF.ZS. Writes geo_employment_by_sector_country_year."""

from geo.models import EmploymentBySectorCountryYear

from . import api

COLUMNS = {
    'SL.AGR.EMPL.ZS': 'agriculture',
    'SL.IND.EMPL.ZS': 'industry',
    'SL.SRV.EMPL.ZS': 'services',
    'SL.EMP.SELF.ZS': 'self_employed',
}


def run():
    return api.load_indicators(EmploymentBySectorCountryYear, COLUMNS)
