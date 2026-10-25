"""Where expert surveys place each compass party, from data/politics/<country>/positions.csv. Writes pol_party_position.

tools/party_positions.py builds that file from the surveys' own data; politics/compass.py describes the surveys.
"""

import csv

from django.db import transaction

from geo.models import EtlLoad
from politics.models import PartyPosition, PartyProfile

from . import COUNTRIES, DATA

SOURCE = 'PREPPS Latam, CHES Latin America and the Global Party Survey, converted and completed by Data Mechanics'


def run():
    positions = []
    for folder, iso3 in COUNTRIES.items():
        path = DATA / folder / 'positions.csv'
        if not path.exists():
            continue
        parties = {party.key: party for party in PartyProfile.objects.filter(country_id=iso3)}
        with open(path, encoding='utf-8') as file:
            positions += [PartyPosition(party=parties[row['party']], survey=row['survey'], name_at_survey=row['name_at_survey'],
                                        economic=float(row['economic']), social=float(row['social']),
                                        experts=int(row['experts']), inferred=row['inferred'],
                                        inferred_from=row['inferred_from'],
                                        economic_fit=float(row['economic_fit']) if row['economic_fit'] else None,
                                        social_fit=float(row['social_fit']) if row['social_fit'] else None)
                          for row in csv.DictReader(file)]
    with transaction.atomic():
        PartyPosition.objects.all().delete()
        PartyPosition.objects.bulk_create(positions)
        EtlLoad.objects.create(table_name=PartyPosition._meta.db_table, source_name=SOURCE,
                               source_url='https://doi.org/10.7910/DVN/TYVFC3', row_count=len(positions))
    return len(positions)
