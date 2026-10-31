"""The House of Commons' members in office and their parties. Writes the United Kingdom's rows of pol_deputy.

Every MP holds a seat, Sinn Féin's abstentionists among them. The Speaker counts as the Speaker, not for a party.
"""

from django.db import transaction

from geo.models import EtlLoad
from politics.congress import HOUSES
from politics.models import Deputy

from . import PAGE_URL, members

SOURCE = HOUSES['GBR']['commons']['source']
COMMONS = 1


def run():
    rows = [Deputy(country_id='GBR', member_id=member_id, name=name, party=party, state='')
            for member_id, name, party in members(COMMONS)]
    with transaction.atomic():
        Deputy.objects.filter(country_id='GBR').delete()  # the other countries' deputies stay
        Deputy.objects.bulk_create(rows)
        EtlLoad.objects.create(table_name=Deputy._meta.db_table, source_name=SOURCE, source_url=PAGE_URL, row_count=len(rows))
    return len(rows)
