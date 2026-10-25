"""The parties the party compass and the seats in Congress show, from data/politics/<country>/party_profiles.csv.
Writes pol_party_profile.

Only a country with that file has a compass and seats.
Parties are updated in place, and one no longer in its country's file is deleted with its positions.
Run providers/curated/party_positions.py next, as the ETL order does.
"""

import csv

from django.db import transaction

from geo.models import EtlLoad
from politics.models import PartyProfile

from . import COUNTRIES, DATA

SOURCE = 'Data Mechanics: positions and ideologies from Wikipedia, logos from Wikimedia Commons'
FIELDS = ('abbreviation', 'name', 'color', 'logo', 'logo_on_dark', 'logo_source', 'logo_licence', 'logo_author',
          'position', 'ideologies', 'views_source', 'merged_into', 'congress')


def run():
    count = 0
    with transaction.atomic():
        for folder, iso3 in COUNTRIES.items():
            path = DATA / folder / 'party_profiles.csv'
            if not path.exists():
                continue
            with open(path, encoding='utf-8') as file:
                rows = list(csv.DictReader(file))
            PartyProfile.objects.filter(country_id=iso3).exclude(key__in=[row['key'] for row in rows]).delete()
            for row in rows:
                PartyProfile.objects.update_or_create(
                    country_id=iso3, key=row['key'],
                    defaults={**{field: row[field] for field in FIELDS},
                              'ended_year': int(row['ended_year']) if row['ended_year'] else None},
                )
                count += 1
        EtlLoad.objects.create(table_name=PartyProfile._meta.db_table, source_name=SOURCE,
                               source_url='https://en.wikipedia.org/', row_count=count)
    return count
