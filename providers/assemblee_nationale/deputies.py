"""France's Assemblée nationale: its deputies in office and their parliamentary groups. Writes France's rows of pol_deputy.

The Assemblée publishes a file of every deputy whose mandate is in force today, with the group each sits in.
A deputy counts for their group, as the Assemblée counts its seats, and each group for its main party
(party_profiles.csv's `congress`), because the deputies' own party field puts Renaissance and MoDem under one label.
A group's "apparentés" count in it. A deputy in no group (NI, non inscrit) counts as no party.
The file's address names the legislature: a dissolution starts the 18th, and LEGISLATURE must follow it.
"""

import csv
import io

from django.db import transaction

from geo.models import EtlLoad
from politics.congress import HOUSES
from politics.models import Deputy
from providers import http

LEGISLATURE = 17  # began on 18 July 2024
URL = (f'https://data.assemblee-nationale.fr/static/openData/repository/{LEGISLATURE}/amo/deputes_actifs_csv_opendata/'
       'liste_deputes_libre_office.csv')
PAGE = 'https://data.assemblee-nationale.fr/acteurs/deputes-en-exercice'
SOURCE = HOUSES['FRA']['assemblee']['source']
NO_GROUP = 'NI'


def run():
    rows = []
    for row in csv.DictReader(io.StringIO(http.get_text(URL, encoding='utf-8-sig'))):
        group = row['Groupe politique (abrégé)'].strip()
        rows.append(Deputy(country_id='FRA', member_id=row['identifiant'], name=f"{row['Prénom']} {row['Nom']}",
                           party='' if group == NO_GROUP else group, state=''))
    with transaction.atomic():
        Deputy.objects.filter(country_id='FRA').delete()  # the other countries' deputies stay
        Deputy.objects.bulk_create(rows)
        EtlLoad.objects.create(table_name=Deputy._meta.db_table, source_name=SOURCE, source_url=PAGE, row_count=len(rows))
    return len(rows)
