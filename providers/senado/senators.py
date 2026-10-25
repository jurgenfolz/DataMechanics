"""The senators in office and their parties, from the Senate's open data. Writes pol_senator.

The list is the house as it is today, substitutes in office included. The Senate writes S/Partido for a senator
without a party; the table keeps that as an empty party.
Each seat keeps the year its eight-year term ends, so the page can tell which senators stay after an election.
"""

import json
import urllib.request

from django.db import transaction

from geo.models import EtlLoad
from politics.models import Senator

URL = 'https://legis.senado.leg.br/dadosabertos/senador/lista/atual.json'
SOURCE = 'Senado Federal, Dados Abertos'
HEADERS = {'User-Agent': 'DataMechanics/1.0 (https://data-mechanics.com)', 'Accept': 'application/json'}
NO_PARTY = 'S/Partido'


def run():
    with urllib.request.urlopen(urllib.request.Request(URL, headers=HEADERS), timeout=60) as response:
        found = json.load(response)['ListaParlamentarEmExercicio']['Parlamentares']['Parlamentar']
    rows = []
    for member in found:
        who = member['IdentificacaoParlamentar']
        party = who.get('SiglaPartidoParlamentar') or ''
        # A term spans two four-year legislatures; it ends with the second.
        ends = member['Mandato']['SegundaLegislaturaDoMandato']['DataFim']
        rows.append(Senator(country_id='BRA', member_id=who['CodigoParlamentar'], name=who['NomeParlamentar'],
                            party='' if party == NO_PARTY else party, state=who.get('UfParlamentar', ''),
                            term_ends=int(ends[:4])))
    with transaction.atomic():
        Senator.objects.all().delete()
        Senator.objects.bulk_create(rows)
        EtlLoad.objects.create(table_name=Senator._meta.db_table, source_name=SOURCE,
                               source_url='https://www12.senado.leg.br/dados-abertos', row_count=len(rows))
    return len(rows)
