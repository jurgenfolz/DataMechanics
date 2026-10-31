"""France's Sénat: its senators in office and their political groups. Writes France's rows of pol_senator.

The Sénat's file lists every senator, past and present, with the group each sits in; "ACTIF" marks those in office.
The file gives no party, so a senator counts for their group, and each group for its main party (party_profiles.csv's
`congress`). A group's "apparentés" and "rattachés" count in it. A senator in no group (NI) counts as no party.
Half the Sénat is elected every three years, the last time on 27 September 2026, so it has no single term: term_ends stays empty.
"""

from django.db import transaction

from geo.models import EtlLoad
from politics.congress import HOUSES
from politics.models import Senator
from providers import http

URL = 'https://data.senat.fr/data/senateurs/ODSEN_GENERAL.json'
PAGE = 'https://data.senat.fr/les-senateurs/'
SOURCE = HOUSES['FRA']['senat']['source']
IN_OFFICE = 'ACTIF'
NO_GROUP = 'NI'


def run():
    rows = []
    for row in http.get_json(URL)['results']:
        if row['Etat'] != IN_OFFICE:
            continue
        group = (row['Groupe_politique'] or '').strip()
        rows.append(Senator(country_id='FRA', member_id=row['Matricule'], name=f"{row['Prenom_usuel']} {row['Nom_usuel']}",
                            party='' if group == NO_GROUP else group, state='', term_ends=None))
    with transaction.atomic():
        Senator.objects.filter(country_id='FRA').delete()  # the other countries' senators stay
        Senator.objects.bulk_create(rows)
        EtlLoad.objects.create(table_name=Senator._meta.db_table, source_name=SOURCE, source_url=PAGE, row_count=len(rows))
    return len(rows)
