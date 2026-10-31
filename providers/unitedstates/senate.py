"""The Senate's members in office and their parties. Writes the United States' rows of pol_senator.

A senator sits for six years and a third of the Senate is elected every two years, so each seat keeps the year its
term ends.
"""

from django.db import transaction

from geo.models import EtlLoad
from politics.congress import HOUSES
from politics.models import Senator

from . import PAGE, check, members, name

SOURCE = HOUSES['USA']['senate']['source']


def run():
    rows = [Senator(country_id='USA', member_id=member['id']['bioguide'], name=name(member), party=term['party'],
                    state=term['state'], term_ends=int(term['end'][:4]))
            for member, term in members('sen')]
    check(rows, HOUSES['USA']['senate']['seats'])
    with transaction.atomic():
        Senator.objects.filter(country_id='USA').delete()  # the other countries' senators stay
        Senator.objects.bulk_create(rows)
        EtlLoad.objects.create(table_name=Senator._meta.db_table, source_name=SOURCE, source_url=PAGE, row_count=len(rows))
    return len(rows)
