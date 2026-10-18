"""Population, births and deaths, from three World Bank indicators. Writes geo_population_country_year.

SP.POP.TOTL is the total population. SP.DYN.CBRT.IN and SP.DYN.CDRT.IN are births and deaths per 1,000 people.
"""

from geo.models import PopulationCountryYear
from providers.load import replace_table

from . import api

# Indicator code -> column in geo_population_country_year.
CODES = {
    'SP.POP.TOTL': 'population',
    'SP.DYN.CBRT.IN': 'birth_rate',
    'SP.DYN.CDRT.IN': 'death_rate',
}


def run():
    rows, updated = {}, ''
    for code, column in CODES.items():
        values, updated = api.fetch_indicator(code)
        for key, value in values.items():
            rows.setdefault(key, dict.fromkeys(CODES.values()))[column] = value
    for fields in rows.values():
        if fields['population'] is not None:
            fields['population'] = round(fields['population'])
    return replace_table(PopulationCountryYear, rows, api.source('SP.POP.TOTL', updated))
