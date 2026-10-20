"""Total meat production (FAO), as published by Our World in Data. Writes geo_meat_production_country_year."""

from geo.models import MeatProductionCountryYear

from . import grapher

CHARTS = {'meat-production-tonnes': {'meat__total__00001765__production__005510__tonnes': 'value'}}


def run():
    return grapher.load_charts(MeatProductionCountryYear, CHARTS)
