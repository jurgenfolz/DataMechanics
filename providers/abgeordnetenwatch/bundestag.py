"""The Bundestag's members in office and their parties, from abgeordnetenwatch.de's API (CC0).
Writes Germany's rows of pol_deputy.

The Bundestag publishes its own list of members, but that file lags months behind and states no licence.
abgeordnetenwatch's list is current and free to reuse.
A member counts for the party they belong to today, not for their parliamentary group: a member who left the AfD group
but not the party still counts for the AfD. A member without a party ("parteilos") counts as no party.
It takes two rounds of requests: the current term's mandates, then their politicians, 150 at a time.
"""

import json
import urllib.parse
import urllib.request
from datetime import date

from django.db import transaction

from geo.models import EtlLoad
from politics.congress import HOUSES
from politics.models import Deputy

API = 'https://www.abgeordnetenwatch.de/api/v2'
PARLIAMENT = 5  # the Bundestag, in abgeordnetenwatch's ids
SOURCE = HOUSES['DEU']['bundestag']['source']
HEADERS = {'User-Agent': 'DataMechanics/1.0 (https://data-mechanics.com)'}
NO_PARTY = 'parteilos'
CHUNK = 150  # politicians asked for in one request


def get(path, params):
    """The `data` of one API response."""
    url = f'{API}/{path}?{urllib.parse.urlencode(params, safe="[],")}'
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as response:
        payload = json.load(response)
    if payload['meta']['status'] != 'ok':
        raise RuntimeError(payload['meta'].get('status_message'))
    return payload['data']


def party_code(label):
    """The party as the site codes it: the Greens' label carries a soft hyphen, and "parteilos" is no party."""
    label = (label or '').replace('­', '').strip()
    return '' if label == NO_PARTY else label


def run():
    # The current term: the latest that has begun. A future one can be listed before its election.
    today = date.today().isoformat()
    periods = [p for p in get('parliament-periods', {'parliament': PARLIAMENT, 'type': 'legislature'})
               if p['start_date_period'] <= today]
    period = max(periods, key=lambda p: p['start_date_period'])
    mandates = [m for m in get('candidacies-mandates', {'parliament_period': period['id'], 'type': 'mandate', 'range_end': 1000})
                if m['end_date'] is None]
    ids = [m['politician']['id'] for m in mandates]
    parties = {}
    for start in range(0, len(ids), CHUNK):
        chunk = '[' + ','.join(map(str, ids[start:start + CHUNK])) + ']'
        for politician in get('politicians', {'id[in]': chunk, 'range_end': 1000}):
            parties[politician['id']] = party_code((politician['party'] or {}).get('label'))
    rows = [Deputy(country_id='DEU', member_id=str(m['politician']['id']), name=m['politician']['label'],
                   party=parties[m['politician']['id']], state='') for m in mandates]
    with transaction.atomic():
        Deputy.objects.filter(country_id='DEU').delete()  # the other countries' deputies stay
        Deputy.objects.bulk_create(rows)
        EtlLoad.objects.create(table_name=Deputy._meta.db_table, source_name=SOURCE,
                               source_url='https://www.abgeordnetenwatch.de/api', row_count=len(rows))
    return len(rows)
