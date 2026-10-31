"""The LGBT+ Policy Index (Velasco), as published by Our World in Data. Writes geo_lgbt_rights_country_year."""

from geo.models import LgbtRightsCountryYear

from . import grapher

CHARTS = {'lgbt-rights-index': {'composite_index': 'value'}}


def run():
    return grapher.load_charts(LgbtRightsCountryYear, CHARTS)
