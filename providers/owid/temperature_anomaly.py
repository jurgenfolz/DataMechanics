"""Yearly temperature anomaly by country, Copernicus ERA5 via Our World in Data. Writes geo_temperature_anomaly_country_year."""

from geo.models import TemperatureAnomalyCountryYear

from . import grapher

CHARTS = {'annual-temperature-anomalies': {'temperature_anomaly': 'value'}}


def run():
    return grapher.load_charts(TemperatureAnomalyCountryYear, CHARTS)
