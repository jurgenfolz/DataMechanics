"""Austria's Bundesrat: its members in office and the parties that sent them, from the Parliament's open data.
Writes Austria's rows of pol_senator.

A group in the Bundesrat needs five members, so its three Greens and its NEOS member sit in no group.
So each member counts for the party they were elected for (Wahlpartei), not for their group.
The Bundesrat has no terms of its own: the states' parliaments send its members, so term_ends stays empty.
"""

from django.db import transaction

from geo.models import EtlLoad
from politics.congress import HOUSES
from politics.models import Senator

from . import members, text

SOURCE = HOUSES['AUT']['bundesrat']['source']


def run():
    # Columns: 0 the member's id, 1 the name, 3 the party they were elected for.
    rows = [Senator(country_id='AUT', member_id=str(row[0]), name=text(row[1]), party=text(row[3]), state='', term_ends=None)
            for row in members('WFW_005', '10005')]
    with transaction.atomic():
        Senator.objects.filter(country_id='AUT').delete()  # the other countries' senators stay
        Senator.objects.bulk_create(rows)
        EtlLoad.objects.create(table_name=Senator._meta.db_table, source_name=SOURCE,
                               source_url='https://www.parlament.gv.at/recherchieren/open-data/', row_count=len(rows))
    return len(rows)
