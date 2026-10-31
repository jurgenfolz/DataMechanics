"""Italy's Senato della Repubblica: its senators in office and their parliamentary groups. Writes Italy's rows of pol_senator.

The Senate's SPARQL endpoint answers a GET (it refuses a POST) with the senators of the XIX legislature: the 200 elected
and the senators for life, who sit in the groups like everyone else.
A senator counts for their group today, by the group's short name (titoloBreve, e.g. FdI), and each group for its party
(party_profiles.csv's `congress`). The Senate's data names no components in its mixed group, so a senator there counts as Misto.
"""

import urllib.parse

from django.db import transaction

from geo.models import EtlLoad
from politics.congress import HOUSES
from politics.models import Senator
from providers import http

ENDPOINT = 'https://dati.senato.it/sparql'
PAGE = 'https://dati.senato.it/'
SOURCE = HOUSES['ITA']['senato']['source']

# A mandate, a group membership or a group name without an end date is the one in force today.
QUERY = """
PREFIX osr: <http://dati.senato.it/osr/>
PREFIX ocd: <http://dati.camera.it/ocd/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
SELECT DISTINCT ?senator ?first ?last ?group WHERE {
  ?senator a osr:Senatore ; foaf:firstName ?first ; foaf:lastName ?last ; osr:mandato ?mandate ; ocd:aderisce ?membership .
  ?mandate osr:legislatura 19 .
  FILTER NOT EXISTS { ?mandate osr:fine ?mandateEnd }
  ?membership osr:legislatura 19 ; osr:gruppo ?g .
  FILTER NOT EXISTS { ?membership osr:fine ?membershipEnd }
  ?g osr:denominazione ?name .
  ?name osr:titoloBreve ?group .
  FILTER NOT EXISTS { ?name osr:fine ?nameEnd }
}
"""


def run():
    url = f"{ENDPOINT}?{urllib.parse.urlencode({'query': QUERY, 'format': 'application/sparql-results+json'})}"
    members = {}
    for row in http.get_json(url)['results']['bindings']:
        # A senator's address ends in their id: http://dati.senato.it/senatore/30110 -> 30110.
        member_id = row['senator']['value'].rstrip('/').rsplit('/', 1)[-1]
        members[member_id] = Senator(country_id='ITA', member_id=member_id, name=f"{row['first']['value']} {row['last']['value']}",
                                     party=row['group']['value'], state='', term_ends=None)
    rows = list(members.values())
    with transaction.atomic():
        Senator.objects.filter(country_id='ITA').delete()  # the other countries' senators stay
        Senator.objects.bulk_create(rows)
        EtlLoad.objects.create(table_name=Senator._meta.db_table, source_name=SOURCE, source_url=PAGE, row_count=len(rows))
    return len(rows)
