"""Italy's Camera dei Deputati: its deputies in office and their parliamentary groups. Writes Italy's rows of pol_deputy.

The Camera's SPARQL endpoint answers a POST with the deputies of the XIX legislature whose mandate has not ended.
The data gives no party, so a deputy counts for their group today, and each group for its party (party_profiles.csv's
`congress`). A deputy in the mixed group (Misto) who sits in one of its political components, which the Camera names
itself (MISTO-+EU-SUEU for +Europa), counts for that component; one in no component counts as Misto.
"""

import json
import urllib.parse
import urllib.request

from django.db import transaction

from geo.models import EtlLoad
from politics.congress import HOUSES
from politics.models import Deputy

ENDPOINT = 'https://dati.camera.it/sparql'
PAGE = 'https://dati.camera.it/'
SOURCE = HOUSES['ITA']['camera']['source']
HEADERS = {'User-Agent': 'DataMechanics ETL (+https://data-mechanics.com)', 'Accept': 'application/sparql-results+json',
           'Content-Type': 'application/x-www-form-urlencoded'}
LEGISLATURE = 'http://dati.camera.it/ocd/legislatura.rdf/repubblica_19'  # began on 13 October 2022

# A mandate, a group membership or a component membership without an end date is the one in force today.
QUERY = """
PREFIX ocd: <http://dati.camera.it/ocd/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
SELECT DISTINCT ?deputy ?first ?last ?group ?component WHERE {
  ?deputy a ocd:deputato ; ocd:rif_leg <%s> ; ocd:rif_mandatoCamera ?mandate ;
          foaf:firstName ?first ; foaf:surname ?last ; ocd:aderisce ?membership .
  FILTER NOT EXISTS { ?mandate ocd:endDate ?mandateEnd }
  ?membership ocd:rif_gruppoParlamentare ?g .
  FILTER NOT EXISTS { ?membership ocd:endDate ?membershipEnd }
  ?g dcterms:alternative ?group .
  OPTIONAL {
    ?c a ocd:componenteGruppoMisto ; ocd:rif_gruppoParlamentare ?g ; dcterms:alternative ?component ; ocd:siComponeDi ?seat .
    FILTER NOT EXISTS { ?c ocd:endDate ?componentEnd }
    ?seat ocd:rif_deputato ?deputy .
    FILTER NOT EXISTS { ?seat ocd:endDate ?seatEnd }
  }
}
""" % LEGISLATURE


def run():
    request = urllib.request.Request(ENDPOINT, data=urllib.parse.urlencode({'query': QUERY}).encode(), headers=HEADERS,
                                     method='POST')
    with urllib.request.urlopen(request, timeout=120) as response:
        bindings = json.load(response)['results']['bindings']
    members = {}
    for row in bindings:
        # A deputy's address ends in their id and the legislature: .../deputato.rdf/d309220_19 -> 309220.
        member_id = row['deputy']['value'].rsplit('/d', 1)[-1].split('_')[0]
        code = row['component']['value'] if 'component' in row else row['group']['value']
        members[member_id] = Deputy(country_id='ITA', member_id=member_id, name=f"{row['first']['value']} {row['last']['value']}",
                                    party=code, state='')
    rows = list(members.values())
    with transaction.atomic():
        Deputy.objects.filter(country_id='ITA').delete()  # the other countries' deputies stay
        Deputy.objects.bulk_create(rows)
        EtlLoad.objects.create(table_name=Deputy._meta.db_table, source_name=SOURCE, source_url=PAGE, row_count=len(rows))
    return len(rows)
