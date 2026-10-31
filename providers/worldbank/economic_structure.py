"""Value added by agriculture, industry and services, % of GDP. Writes geo_economic_structure_country_year."""

from geo.models import EconomicStructureCountryYear

from . import api

COLUMNS = {
    'NV.AGR.TOTL.ZS': 'agriculture',
    'NV.IND.TOTL.ZS': 'industry',
    'NV.SRV.TOTL.ZS': 'services',
}
# Each sector's value added in local currency, to drop the shares the World Bank rounded away (Brazil before 1985).
AMOUNTS = {
    'NV.AGR.TOTL.ZS': ['NV.AGR.TOTL.CN'],
    'NV.IND.TOTL.ZS': ['NV.IND.TOTL.CN'],
    'NV.SRV.TOTL.ZS': ['NV.SRV.TOTL.CN'],
}


def run():
    return api.load_indicators(EconomicStructureCountryYear, COLUMNS, amounts=AMOUNTS)
