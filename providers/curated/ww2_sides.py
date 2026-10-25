"""Which side each state fought on, and when, from data/ww2/sides.csv. Writes ww2.state_side.

The dates are those of Wikipedia's list of declarations of war; a state without a row was not at war.
Run providers/curated/ww2_states.py first.
"""

from conflicts.models import Side
from providers.load import Source, replace_rows

from . import optional_date, ww2_rows

SOURCE = Source(
    name='Wikipedia, "Declarations of war during World War II"',
    url='https://en.wikipedia.org/w/index.php?title=Declarations_of_war_during_World_War_II&oldid=1381772799',
)


def run():
    objects = [Side(state_id=row['code'], side=row['side'], start=optional_date(row['start']),
                    end=optional_date(row['end']), note=row['note'])
               for row in ww2_rows('sides.csv')]
    return replace_rows(Side, objects, SOURCE)
