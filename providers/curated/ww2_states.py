"""States and territories of 1937–1945, from data/ww2/states.csv, with their flags from data/ww2/flags.csv.
Writes ww2.state.

States are updated in place, so the tables that point at them keep their links.
A state no longer in the file is deleted.
"""

from django.db import router, transaction

from conflicts.models import State
from providers.load import Source, log_load

from . import optional_date, ww2_rows

SOURCE = Source(name='Data Mechanics, compiled from Wikipedia and Wikidata; flags from Wikimedia Commons',
                url='https://commons.wikimedia.org/')
FLAGS = 'conflicts/ww2/flags'


def run():
    rows = ww2_rows('states.csv')
    flags = {row['code']: row for row in ww2_rows('flags.csv')}
    with transaction.atomic(using=router.db_for_write(State)):
        State.objects.exclude(code__in=[row['code'] for row in rows]).delete()
        for row in rows:
            flag = flags[row['code']]
            State.objects.update_or_create(code=row['code'], defaults={
                'name': row['name'],
                'name_de': row['name_de'],
                'name_pt': row['name_pt'],
                'kind': row['kind'],
                'successors': row['successors'].split(),
                'wikidata': row['qid'],
                'gwcodes': [int(code) for code in row['gwcodes'].split()],
                'start': optional_date(row['start']),
                'end': optional_date(row['end']),
                'flag': f"{FLAGS}/{row['code']}.svg",
                'flag_source': flag['source'],
                'flag_licence': flag['licence'],
                'flag_author': flag['author'],
            })
        # A ruler is another state, so rulers are set once every state exists.
        for row in rows:
            State.objects.filter(code=row['code']).update(ruler_id=row['ruler'] or None)
    log_load(State, SOURCE, len(rows))
    return len(rows)
