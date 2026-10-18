"""Who governed when, and for which party, from data/politics/<country>/administrations.csv. Writes pol_administration.

One row per stretch in office under one party, so a leader who changes party mid-term has several rows.
Run providers/curated/parties.py first: rows point at its parties by abbreviation.
"""

import csv
from datetime import date

from django.db import transaction

from geo.models import EtlLoad
from politics.models import Administration, Party

from . import COUNTRIES, DATA

SOURCE = 'Data Mechanics, compiled from Wikipedia'


def run():
    objects = []
    for folder, iso3 in COUNTRIES.items():
        parties = {party.abbreviation: party for party in Party.objects.filter(country_id=iso3)}
        with open(DATA / folder / 'administrations.csv', encoding='utf-8') as file:
            for row in csv.DictReader(file):
                objects.append(Administration(
                    country_id=iso3,
                    leader=row['leader'],
                    short_name=row['short_name'],
                    role=row['role'],
                    party=parties[row['party']] if row['party'] else None,
                    start_date=date.fromisoformat(row['start_date']),
                    end_date=date.fromisoformat(row['end_date']) if row['end_date'] else None,
                    notes=row['notes'],
                    source_url=row['source_url'],
                ))
    with transaction.atomic():
        Administration.objects.filter(country_id__in=COUNTRIES.values()).delete()
        Administration.objects.bulk_create(objects)
        EtlLoad.objects.create(table_name=Administration._meta.db_table, source_name=SOURCE,
                               source_url=objects[0].source_url if objects else '', row_count=len(objects))
    return len(objects)
