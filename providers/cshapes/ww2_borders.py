"""Borders of 1937–1945 from CShapes 2.0, simplified for a world map. Writes ww2.border.

CShapes dates every border it draws, and draws them as the law saw them: occupations during the war are not in it.
A shape belongs to a state of ww2.state through its Gleditsch–Ward code (the state's gwcodes).
Colonies without a state of their own name their ruler in data/ww2/territories.csv (none for a free city).
A shape in neither stops the load.
"""

from datetime import date

from conflicts.models import Border, State
from providers import geometry, http
from providers.curated import ww2_rows
from providers.load import Source, replace_rows

URL = 'https://icr.ethz.ch/data/cshapes/CShapes-2.0.geojson'
SOURCE = Source(name='CShapes 2.0, ETH Zürich (CC BY-NC-SA 4.0)', url='https://icr.ethz.ch/data/cshapes/',
                updated='2.0')
FIRST, LAST = date(1937, 7, 7), date(1945, 9, 2)
# Simplification tolerance and rounding, in degrees: about 10 km, finer than a world map shows.
TOLERANCE = 0.1
DECIMALS = 2


def run():
    states = {code: state.code for state in State.objects.all() for code in state.gwcodes}
    territories = {int(row['gwcode']): row for row in ww2_rows('territories.csv')}
    objects = []
    for feature in http.get_json(URL, timeout=600)['features']:
        p = feature['properties']
        start = date(p['gwsyear'], p['gwsmonth'], p['gwsday'])
        end = date(p['gweyear'], p['gwemonth'], p['gweday'])
        if start > LAST or end < FIRST:
            continue
        code = p['gwcode']
        if code not in states and code not in territories:
            raise ValueError(f"CShapes shape {code} ({p['cntry_name']}) has no state: add it to data/ww2/territories.csv.")
        objects.append(Border(
            gwcode=code, start=start, end=end, state_id=states.get(code),
            # A colony takes its name of the time from territories.csv: CShapes names it as the country it became.
            name=p['cntry_name'] if code in states else territories[code]['name'],
            ruler_id=None if code in states else territories[code]['ruler'] or None,
            geometry=geometry.simplify(feature['geometry'], TOLERANCE, DECIMALS),
        ))
    return replace_rows(Border, objects, SOURCE)
