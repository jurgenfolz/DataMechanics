"""The deputies and senators elected in Brazil's last general election, from the electoral court's open data.
Writes pol_elected.

The court's candidate file lists every candidate with the result of the count.
A deputy is elected by the party quotient (QP) or by the largest averages (média); a senator by the most votes.
They take office on 1 February of the next year (politics/congress.py).
Each keeps the party they ran for.
"""

import csv
import io
import urllib.request
import zipfile
from datetime import datetime

from django.db import transaction

from geo.models import EtlLoad
from politics.congress import ELECTION_SOURCE
from politics.models import Elected

ELECTION = 2026
URL = f'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_{ELECTION}.zip'
MEMBER = f'consulta_cand_{ELECTION}_BRASIL.csv'  # every state in one file
SOURCE = ELECTION_SOURCE
SOURCE_URL = f'https://dadosabertos.tse.jus.br/dataset/candidatos-{ELECTION}'
HEADERS = {'User-Agent': 'DataMechanics/1.0 (https://data-mechanics.com)'}
HOUSES = {'DEPUTADO FEDERAL': 'chamber', 'SENADOR': 'senate'}
WON = {'ELEITO', 'ELEITO POR QP', 'ELEITO POR MÉDIA'}


def candidates():
    """The rows of the court's candidate file, one per candidate and round."""
    with urllib.request.urlopen(urllib.request.Request(URL, headers=HEADERS), timeout=120) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    with archive.open(MEMBER) as file:
        return list(csv.DictReader(io.TextIOWrapper(file, encoding='latin-1'), delimiter=';'))


def elected(rows):
    """The members elected to the two houses, as unsaved Elected rows."""
    return [Elected(country_id='BRA', member_id=row['SQ_CANDIDATO'], name=row['NM_URNA_CANDIDATO'], party=row['SG_PARTIDO'],
                    state=row['SG_UF'], house=HOUSES[row['DS_CARGO']],
                    elected_on=datetime.strptime(row['DT_ELEICAO'], '%d/%m/%Y').date())
            for row in rows if row['DS_CARGO'] in HOUSES and row['DS_SIT_TOT_TURNO'] in WON]


def run():
    rows = elected(candidates())
    with transaction.atomic():
        Elected.objects.all().delete()
        Elected.objects.bulk_create(rows)
        EtlLoad.objects.create(table_name=Elected._meta.db_table, source_name=SOURCE, source_url=SOURCE_URL, row_count=len(rows))
    return len(rows)
