"""Crime suspects by nationality and kind of offence, from data/politics/<country>/suspects.csv.
Writes pol_suspects_nationality_offence.

tools/germany_suspects.py builds Germany's file from the police crime statistics (table T62); politics/crime.py names the
kinds of offence.
"""

import csv

from politics.models import Suspects
from providers.load import Source, replace_rows

from . import COUNTRIES, DATA

SOURCE = Source('Bundeskriminalamt, Polizeiliche Kriminalstatistik',
                ('https://www.bka.de/DE/AktuelleInformationen/StatistikenLagebilder/PolizeilicheKriminalstatistik/PKS2025/'
                 'pksTabellen_Interpretationshilfen/BundTVNationalitaet/bundTVNationalitaet.html'))


def run():
    rows = []
    for folder, iso3 in COUNTRIES.items():
        path = DATA / folder / 'suspects.csv'
        if not path.exists():
            continue
        with open(path, encoding='utf-8') as file:
            rows += [Suspects(country_id=iso3, nationality_id=row['nationality'] or None, year=int(row['year']),
                              offence=row['offence'], suspects=int(row['suspects']))
                     for row in csv.DictReader(file)]
    return replace_rows(Suspects, rows, SOURCE)
