"""Key events of World War II for the timeline, from data/ww2/events.csv. Writes ww2.event.

Each date was checked against English Wikipedia (the row's pinned source); the labels are our own words.
"""

from conflicts.models import Event
from providers.load import Source, replace_rows

from . import optional_date, ww2_rows

SOURCE = Source(name='Data Mechanics, compiled from Wikipedia and Wikidata', url='https://en.wikipedia.org/')


def run():
    objects = [Event(date=optional_date(row['date']), kind=row['kind'], region=row['region'], name=row['name'], name_de=row['name_de'],
                     name_pt=row['name_pt'], wikidata=row['qid'], source_url=row['source'])
               for row in ww2_rows('events.csv')]
    return replace_rows(Event, objects, SOURCE)
