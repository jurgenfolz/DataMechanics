"""Oil and coal production in terawatt-hours, Energy Institute and historical sources via Our World in Data. Writes geo_fossil_fuel_production_country_year."""

from geo.models import FossilFuelProductionCountryYear

from . import grapher

CHARTS = {
    'oil-production-by-country': {'oil_production_twh': 'oil'},
    'coal-production-by-country': {'coal_production_twh': 'coal'},
}


def run():
    return grapher.load_charts(FossilFuelProductionCountryYear, CHARTS)
