"""Political parties, from data/politics/<country>/parties.csv. Writes pol_party.

Parties are updated in place, so the administrations that point at them keep their links.
A party no longer in its country's file is deleted; run providers/curated/administrations.py next, as the ETL order does.
"""

import csv

from django.db import transaction

from geo.models import EtlLoad
from politics.models import Party

from . import COUNTRIES, DATA

SOURCE = 'Data Mechanics, compiled from Wikipedia; logos from Wikimedia Commons'


def run():
    count = 0
    with transaction.atomic():
        for folder, iso3 in COUNTRIES.items():
            with open(DATA / folder / 'parties.csv', encoding='utf-8') as file:
                rows = list(csv.DictReader(file))
                Party.objects.filter(country_id=iso3).exclude(abbreviation__in=[row['abbreviation'] for row in rows]).delete()
                for row in rows:
                    Party.objects.update_or_create(
                        country_id=iso3,
                        abbreviation=row['abbreviation'],
                        defaults={key: row[key] for key in
                                  ('name', 'color', 'logo', 'logo_source', 'logo_licence', 'logo_author')},
                    )
                    count += 1
        EtlLoad.objects.create(table_name=Party._meta.db_table, source_name=SOURCE,
                               source_url='https://commons.wikimedia.org/', row_count=count)
    return count
