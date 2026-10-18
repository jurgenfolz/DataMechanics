"""Female labour force participation, % of women 15+ (ILO modelled estimate), World Bank indicator SL.TLF.CACT.FE.ZS. Writes geo_female_labour_country_year."""

from geo.models import FemaleLabourCountryYear

from . import api

CODE = 'SL.TLF.CACT.FE.ZS'


def run():
    return api.load_indicator(FemaleLabourCountryYear, CODE)
