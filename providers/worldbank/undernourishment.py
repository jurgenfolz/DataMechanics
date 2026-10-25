"""The share of people who are undernourished (FAO), World Bank indicator SN.ITK.DEFC.ZS. Writes geo_undernourishment_country_year.

The FAO publishes no share below 2.5%: the World Bank shows those years as 2.5.
"""

from geo.models import UndernourishmentCountryYear

from . import api

CODE = 'SN.ITK.DEFC.ZS'


def run():
    return api.load_indicator(UndernourishmentCountryYear, CODE)
