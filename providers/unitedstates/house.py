"""The House of Representatives' members in office and their parties. Writes the United States' rows of pol_deputy.

The House's non-voting delegates are left out: the half circle shows the 435 voting seats.
"""

from django.db import transaction

from geo.models import EtlLoad
from politics.congress import HOUSES
from politics.models import Deputy

from . import NON_VOTING, PAGE, check, members, name

SOURCE = HOUSES['USA']['house']['source']


def run():
    rows = [Deputy(country_id='USA', member_id=member['id']['bioguide'], name=name(member), party=term['party'],
                   state=term['state'])
            for member, term in members('rep') if term['state'] not in NON_VOTING]
    check(rows, HOUSES['USA']['house']['seats'])
    with transaction.atomic():
        Deputy.objects.filter(country_id='USA').delete()  # the other countries' deputies stay
        Deputy.objects.bulk_create(rows)
        EtlLoad.objects.create(table_name=Deputy._meta.db_table, source_name=SOURCE, source_url=PAGE, row_count=len(rows))
    return len(rows)
