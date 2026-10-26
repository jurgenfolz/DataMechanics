"""The deputies in office and their parties, from the Chamber's open data. Writes Brazil's rows of pol_deputy.

The list is the house as it is today: a deputy who changed party counts for the new one, and a substitute in office
counts instead of the member they stand in for.
"""

import json
import urllib.request

from django.db import transaction

from geo.models import EtlLoad
from politics.congress import HOUSES
from politics.models import Deputy

URL = 'https://dadosabertos.camara.leg.br/api/v2/deputados?itens=100&ordem=ASC&ordenarPor=nome'
SOURCE = HOUSES['BRA']['chamber']['source']
HEADERS = {'User-Agent': 'DataMechanics/1.0 (https://data-mechanics.com)', 'Accept': 'application/json'}


def members():
    """Every deputy in office, page by page."""
    url, found = URL, []
    while url:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as response:
            page = json.load(response)
        found += page['dados']
        url = next((link['href'] for link in page.get('links', []) if link['rel'] == 'next'), None)
    return found


def run():
    rows = [Deputy(country_id='BRA', member_id=str(m['id']), name=m['nome'], party=m['siglaPartido'] or '', state=m['siglaUf'])
            for m in members()]
    with transaction.atomic():
        Deputy.objects.filter(country_id='BRA').delete()  # the other countries' deputies stay
        Deputy.objects.bulk_create(rows)
        EtlLoad.objects.create(table_name=Deputy._meta.db_table, source_name=SOURCE,
                               source_url='https://dadosabertos.camara.leg.br/', row_count=len(rows))
    return len(rows)
