"""The people of each nationality living in a country, from data/politics/<country>/population.csv.
Writes pol_population_nationality.

tools/germany_suspects.py builds Germany's file from Destatis: the Central Register of Foreigners and the population update.
"""

import csv

from politics.models import NationalityPopulation
from providers.load import Source, replace_rows

from . import COUNTRIES, DATA

SOURCE = Source('Statistisches Bundesamt (Destatis): Ausländerzentralregister and Bevölkerungsfortschreibung',
                'https://genesis.destatis.de/datenbank/online/statistic/12521/table/12521-0002')


def run():
    rows = []
    for folder, iso3 in COUNTRIES.items():
        path = DATA / folder / 'population.csv'
        if not path.exists():
            continue
        with open(path, encoding='utf-8') as file:
            rows += [NationalityPopulation(country_id=iso3, nationality_id=row['nationality'] or None, year=int(row['year']),
                                           source_name=row['source_name'], population=int(row['population']))
                     for row in csv.DictReader(file)]
    return replace_rows(NationalityPopulation, rows, SOURCE)
