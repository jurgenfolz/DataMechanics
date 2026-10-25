"""Where political scientists place each party on one left-right scale, from data/politics/<country>/left_right.csv.
Writes pol_party_left_right.

tools/party_left_right.py builds that file from the survey's own data; politics/spectrum.py describes the survey.
"""

import csv

from django.db import transaction

from geo.models import EtlLoad
from politics.models import PartyLeftRight, PartyProfile

from . import COUNTRIES, DATA

SOURCE = 'Bolognesi, Codato, Ribeiro and Silva: ideological classification of all Brazilian parties, 2022 wave'


def run():
    rows = []
    for folder, iso3 in COUNTRIES.items():
        path = DATA / folder / 'left_right.csv'
        if not path.exists():
            continue
        parties = {party.key: party for party in PartyProfile.objects.filter(country_id=iso3)}
        with open(path, encoding='utf-8') as file:
            rows += [PartyLeftRight(party=parties[row['party']], score=float(row['score']), experts=int(row['experts']),
                                    inferred_from=row['inferred_from'])
                     for row in csv.DictReader(file)]
    with transaction.atomic():
        PartyLeftRight.objects.all().delete()
        PartyLeftRight.objects.bulk_create(rows)
        EtlLoad.objects.create(table_name=PartyLeftRight._meta.db_table, source_name=SOURCE,
                               source_url='https://doi.org/10.7910/DVN/MFIXKW', row_count=len(rows))
    return len(rows)
