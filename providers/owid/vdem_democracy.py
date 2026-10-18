"""The five V-Dem democracy indices, as published by Our World in Data. Writes geo_democracy_country_year.

V-Dem (Varieties of Democracy) produces the indices. Our World in Data republishes them as one chart each.
"""

from geo.models import DemocracyCountryYear

from . import grapher

# Our World in Data chart -> {CSV column: column in geo_democracy_country_year}.
CHARTS = {
    'electoral-democracy-index': {'electdem_vdem__estimate_best': 'electoral'},
    'liberal-democracy-index': {'libdem_vdem__estimate_best': 'liberal'},
    'participatory-democracy-index': {'participdem_vdem__estimate_best': 'participatory'},
    'deliberative-democracy-index-vdem': {'delibdem_vdem__estimate_best': 'deliberative'},
    'egalitarian-democracy-index-vdem': {'egaldem_vdem__estimate_best': 'egalitarian'},
}


def run():
    return grapher.load_charts(DemocracyCountryYear, CHARTS)
