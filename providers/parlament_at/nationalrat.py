"""Austria's Nationalrat: its members in office and their parliamentary clubs, from the Parliament's open data.
Writes Austria's rows of pol_deputy.

A member counts for their club today, which follows them when they leave their party: one expelled from the NEOS club
sits in no club ("OK") and counts as no party.
"""

from django.db import transaction

from geo.models import EtlLoad
from politics.congress import HOUSES
from politics.models import Deputy

from . import members, text

SOURCE = HOUSES['AUT']['nationalrat']['source']
NO_CLUB = 'OK'  # ohne Klubzugehörigkeit


def run():
    # Columns: 0 the name, 9 the club's code, 11 the link to the member's page, which ends in their id.
    rows = []
    for row in members('WFW_002', '10002'):
        club = text(row[9])
        rows.append(Deputy(country_id='AUT', member_id=row[11].rstrip('/').rsplit('/', 1)[-1], name=text(row[0]),
                           party='' if club == NO_CLUB else club, state=''))
    with transaction.atomic():
        Deputy.objects.filter(country_id='AUT').delete()  # the other countries' deputies stay
        Deputy.objects.bulk_create(rows)
        EtlLoad.objects.create(table_name=Deputy._meta.db_table, source_name=SOURCE,
                               source_url='https://www.parlament.gv.at/recherchieren/open-data/', row_count=len(rows))
    return len(rows)
