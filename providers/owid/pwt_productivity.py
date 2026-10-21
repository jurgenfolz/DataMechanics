"""Output per hour worked (Penn World Table), as published by Our World in Data. Writes geo_labour_productivity_country_year."""

from geo.models import LabourProductivityCountryYear

from . import grapher

CHARTS = {'labor-productivity-per-hour-pennworldtable': {'productivity': 'value'}}


def run():
    return grapher.load_charts(LabourProductivityCountryYear, CHARTS)
