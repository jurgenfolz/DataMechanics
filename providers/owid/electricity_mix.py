"""Share of electricity by source, Ember via Our World in Data. Writes geo_electricity_mix_country_year."""

from geo.models import ElectricityMixCountryYear

from . import grapher

_SOURCES = ['coal', 'gas', 'oil', 'nuclear', 'hydro', 'wind', 'solar', 'bioenergy']

CHARTS = {
    'share-elec-by-source': {
        **{f'{name}_share_of_electricity__pct': name for name in _SOURCES},
        'other_renewables_excluding_bioenergy_share_of_electricity__pct': 'other_renewables',
    },
    'share-electricity-low-carbon': {'low_carbon_share_of_electricity__pct': 'low_carbon'},
}


def run():
    return grapher.load_charts(ElectricityMixCountryYear, CHARTS)
