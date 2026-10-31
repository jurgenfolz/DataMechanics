"""States, Länder and provinces of the countries the site maps by state, from Natural Earth's 1:10m admin-1 units.
Writes geo_state.

Natural Earth gives each its ISO 3166-2 code, its border and its names.
Far-off parts (Alaska, the French overseas départements) are drawn as insets beside the mainland (INSETS), and units
a country's data does not set apart are merged (MERGED).
Shapes are simplified to about a kilometre, which a map of one country does not show.
"""

from django.db import transaction

from geo.models import EtlLoad, State
from providers import geometry, http

from .countries import VERSION

URL = f'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{VERSION}/geojson/ne_10m_admin_1_states_provinces.geojson'
SOURCE_PAGE = 'https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/'

COUNTRIES = ('DEU', 'BRA', 'FRA', 'USA', 'ITA', 'AUT')  # the countries with crime by state (politics/crime_series.py)

# Far-off parts drawn as insets beside the mainland, as atlases do: their scale and where their centre goes (lon, lat).
# Alaska and Hawaii go under the contiguous states, the French overseas départements in a column west of Brittany.
INSETS = {
    'US-AK': (0.35, (-118, 27)),
    'US-HI': (1.5, (-103, 25.5)),
    'FR-GP': (1.5, (-7.5, 50.5)),
    'FR-MQ': (2, (-7.5, 48.8)),
    'FR-GF': (0.25, (-7.5, 47)),
    'FR-RE': (2, (-7.5, 45.3)),
    'FR-YT': (3, (-7.5, 43.8)),
}
# Units merged into one state, with the merged state's code: Italy's crime data keeps Sardinia's four provinces at their
# borders of 2001, before Natural Earth's eight (the four made in 2005 went back into them in 2016).
MERGED = {
    'IT-CA': ('IT-CA', 'IT-CI', 'IT-VS'),
    'IT-SS': ('IT-SS', 'IT-OT'),
    'IT-NU': ('IT-NU', 'IT-OG'),
}

# Simplification tolerance and rounding, in degrees. 0.01° is about a kilometre.
TOLERANCE = 0.01
DECIMALS = 3

# Where Natural Earth's name doesn't suit the site, by ISO 3166-2 code and language.
# The Portuguese is Brazilian.
NAME_FIXES = {
    'BR-DF': {'en': 'Federal District', 'pt': 'Distrito Federal'},
    'DE-HB': {'en': 'Bremen', 'de': 'Bremen'},
    'DE-SN': {'pt': 'Saxônia'},
    'US-DC': {'en': 'District of Columbia', 'de': 'District of Columbia', 'pt': 'Distrito de Colúmbia'},
    'FR-64': {'en': 'Pyrénées-Atlantiques', 'de': 'Pyrénées-Atlantiques'},
    'FR-RE': {'en': 'Réunion', 'de': 'Réunion', 'pt': 'Reunião'},
    'IT-GE': {'en': 'Genoa', 'de': 'Genua', 'pt': 'Gênova'},
    'IT-BZ': {'en': 'South Tyrol', 'de': 'Südtirol', 'pt': 'Tirol do Sul'},
    'IT-TN': {'en': 'Trento', 'de': 'Trient', 'pt': 'Trento'},
    'IT-ME': {'de': 'Messina'},
    'IT-KR': {'en': 'Crotone', 'de': 'Crotone', 'pt': 'Crotone'},
}
# Natural Earth prefixes most German names of French départements with the word; the site drops it.
DROPPED_PREFIX = 'Département '


def run():
    features = [feature for feature in http.get_json(URL)['features'] if feature['properties']['adm0_a3'] in COUNTRIES]
    by_code = {feature['properties']['iso_3166_2']: feature for feature in features}
    merged_away = {code for codes in MERGED.values() for code in codes} - set(MERGED)
    states = []
    for feature in features:
        code = feature['properties']['iso_3166_2']
        if code in merged_away:
            continue
        shape = feature['geometry']
        if code in MERGED:
            shape = geometry.dissolve([_multi(by_code[part]['geometry']) for part in MERGED[code]])
        if code in INSETS:
            shape = geometry.moved(shape, *INSETS[code])
        states.append(_state(feature, shape))
    with transaction.atomic():
        State.objects.all().delete()
        State.objects.bulk_create(states)
        EtlLoad.objects.create(table_name=State._meta.db_table, source_name='Natural Earth, Admin 1 states and provinces (1:10m)',
                               source_url=SOURCE_PAGE, source_updated=VERSION, row_count=len(states))
    return len(states)


def _multi(shape):
    """A Polygon or MultiPolygon as a MultiPolygon."""
    if shape['type'] == 'Polygon':
        return {'type': 'MultiPolygon', 'coordinates': [shape['coordinates']]}
    return shape


def _state(feature, shape):
    p = feature['properties']
    code = p['iso_3166_2']
    fixes = NAME_FIXES.get(code, {})
    return State(
        code=code,
        country_id=p['adm0_a3'],
        name=fixes.get('en', p['name_en']),
        name_de=fixes.get('de', (p['name_de'] or '').removeprefix(DROPPED_PREFIX)),
        name_pt=fixes.get('pt', p['name_pt'] or ''),
        geometry=geometry.simplify(shape, TOLERANCE, DECIMALS),
    )
