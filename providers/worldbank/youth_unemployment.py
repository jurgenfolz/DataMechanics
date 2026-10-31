"""Youth unemployment (15 to 24), ILO modelled estimates via the World Bank. Writes geo_youth_unemployment_country_year."""

from geo.models import YouthUnemploymentCountryYear

from . import api

CODE = 'SL.UEM.1524.ZS'


def run():
    return api.load_indicator(YouthUnemploymentCountryYear, CODE)
