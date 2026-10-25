"""The country dimension, from Natural Earth's 1:50m countries. Writes geo_country.

Natural Earth gives every country its ISO codes and its border shape.
Shapes are simplified here so a world map stays small enough to load on every metric page.
Names come in English, German and Portuguese. The site's Portuguese is Brazilian, and Natural Earth writes Portugal's.
"""

from django.db import transaction

from geo.models import Country, EtlLoad
from providers import geometry, http
from providers.load import WORLD, country_code

VERSION = 'v5.1.2'
URL = f'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{VERSION}/geojson/ne_50m_admin_0_countries.geojson'
SOURCE_PAGE = 'https://www.naturalearthdata.com/downloads/50m-cultural-vectors/50m-admin-0-countries-2/'

# Simplification tolerance and rounding, in degrees. 0.05° is about 5 km: invisible on a world map.
TOLERANCE = 0.05
DECIMALS = 2

# Where Natural Earth's name doesn't suit the site, by Natural Earth's ADM0_A3 code.
# German: the short common name. Portuguese: the Brazilian spelling.
NAME_FIXES = {
    'de': {
        'CHN': 'China', 'TWN': 'Taiwan', 'CYP': 'Zypern', 'CYN': 'Nordzypern', 'FSM': 'Mikronesien',
        'CYM': 'Kaimaninseln',
    },
    'pt': {
        'ARM': 'Armênia', 'BEN': 'Benin', 'BLM': 'São Bartolomeu', 'CYM': 'Ilhas Cayman', 'CYN': 'Chipre do Norte',
        'CZE': 'Tchéquia', 'DJI': 'Djibuti', 'EST': 'Estônia', 'IRL': 'Irlanda', 'IRN': 'Irã', 'KAS': 'Geleira de Siachen',
        'KEN': 'Quênia', 'LVA': 'Letônia', 'MCO': 'Mônaco', 'MDG': 'Madagascar', 'MKD': 'Macedônia do Norte',
        'MUS': 'Maurício', 'NCL': 'Nova Caledônia', 'POL': 'Polônia', 'ROU': 'Romênia', 'SVN': 'Eslovênia',
        'SXM': 'Sint Maarten', 'TKM': 'Turcomenistão', 'VNM': 'Vietnã', 'YEM': 'Iêmen',
    },
}


def run():
    features = http.get_json(URL)['features']
    own_codes = {feature['properties']['ADM0_A3'] for feature in features}
    countries = [_country(feature, own_codes) for feature in features]
    countries.append(Country(iso3=WORLD, iso2='', name='World', name_de='Welt', name_pt='Mundo', is_aggregate=True))

    with transaction.atomic():
        for country in countries:
            Country.objects.update_or_create(
                iso3=country.iso3,
                defaults={field: getattr(country, field) for field in
                          ('iso2', 'name', 'name_de', 'name_pt', 'continent', 'subregion', 'is_aggregate', 'geometry')},
            )
        EtlLoad.objects.create(
            table_name=Country._meta.db_table,
            source_name='Natural Earth, Admin 0 countries (1:50m)',
            source_url=SOURCE_PAGE,
            source_updated=VERSION,
            row_count=len(countries),
        )
    return len(countries)


def _country(feature, own_codes):
    p = feature['properties']
    # ISO_A3_EH fills most gaps in ISO_A3; the few units without an ISO code keep Natural Earth's own code.
    iso3 = p['ISO_A3_EH'] if p['ISO_A3_EH'] != '-99' else p['ADM0_A3']
    # Some territories carry their country's code (Ashmore and Cartier Islands say AUS).
    # They keep their own code, so they never overwrite the country itself.
    if iso3 != p['ADM0_A3'] and iso3 in own_codes:
        iso3 = p['ADM0_A3']
    iso2 = p['ISO_A2_EH'] if p['ISO_A2_EH'] != '-99' else ''
    # The shorter of the common name and the long name, skipping abbreviations like "Dem. Rep. Congo".
    spelled_out = [n for n in (p['NAME'], p['NAME_LONG']) if '.' not in n]
    name = min(spelled_out, key=len) if spelled_out else p['NAME_LONG']
    return Country(
        iso3=country_code(iso3),
        iso2=iso2.lower(),
        name=name,
        name_de=NAME_FIXES['de'].get(p['ADM0_A3'], p.get('NAME_DE') or ''),
        name_pt=NAME_FIXES['pt'].get(p['ADM0_A3'], p.get('NAME_PT') or ''),
        continent=p['CONTINENT'],
        subregion=p['SUBREGION'],
        geometry=geometry.simplify(feature['geometry'], TOLERANCE, DECIMALS),
    )

