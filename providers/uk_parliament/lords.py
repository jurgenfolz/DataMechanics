"""The House of Lords' members who can sit today and their parties or groups. Writes the United Kingdom's rows of pol_senator.

The Lords has no fixed size and no terms. IsEligible=true leaves out peers on leave of absence, disqualified or
suspended, which gives the same total as Parliament's own "State of the parties".
"""

from django.db import transaction

from geo.models import EtlLoad
from politics.congress import HOUSES
from politics.models import Senator

from . import PAGE_URL, members

SOURCE = HOUSES['GBR']['lords']['source']
LORDS = 2


def run():
    rows = [Senator(country_id='GBR', member_id=member_id, name=name, party=party, state='', term_ends=None)
            for member_id, name, party in members(LORDS, '&IsEligible=true')]
    with transaction.atomic():
        Senator.objects.filter(country_id='GBR').delete()  # the other countries' senators stay
        Senator.objects.bulk_create(rows)
        EtlLoad.objects.create(table_name=Senator._meta.db_table, source_name=SOURCE, source_url=PAGE_URL, row_count=len(rows))
    return len(rows)
