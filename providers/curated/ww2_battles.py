"""Battles and campaigns of World War II with their casualties per side, from data/ww2/battles.csv.
Writes ww2.battle.

Each row comes from the battle's English Wikipedia infobox (its pinned revision is the row's source) and Wikidata.
Casualties are killed, wounded, missing and captured, from the lowest to the highest estimate the infobox gives.
A battle's picture, from Wikimedia Commons, is in data/ww2/battle_images.csv with its licence and author.
"""

from conflicts.models import Battle, State
from providers.load import Source, replace_rows

from . import WW2, optional_date, ww2_rows

SOURCE = Source(name='Data Mechanics, compiled from Wikipedia and Wikidata', url='https://en.wikipedia.org/')


IMAGES = 'conflicts/ww2/battles'


def run():
    known = set(State.objects.values_list('code', flat=True))
    images = {row['qid']: row for row in ww2_rows('battle_images.csv')} if (WW2 / 'battle_images.csv').exists() else {}
    objects = []
    for row in ww2_rows('battles.csv'):
        image = images.get(row['qid'])
        axis, allies = row['axis'].split(), row['allies'].split()
        unknown = set(axis + allies) - known
        if unknown:
            raise ValueError(f"{row['name']}: {', '.join(sorted(unknown))} not in ww2.state.")
        objects.append(Battle(
            wikidata=row['qid'], name=row['name'], name_de=row['name_de'], name_pt=row['name_pt'],
            theatre=row['theatre'], start=optional_date(row['start']), end=optional_date(row['end']),
            latitude=float(row['lat']), longitude=float(row['lon']), axis=axis, allies=allies,
            axis_low=_count(row['axis_low']), axis_high=_count(row['axis_high']),
            allies_low=_count(row['allies_low']), allies_high=_count(row['allies_high']),
            winner=row['winner'], source_url=row['source'], note=row['note'],
            image=f"{IMAGES}/{row['qid']}.jpg" if image else '', image_source=image['source'] if image else '',
            image_licence=image['licence'] if image else '', image_author=image['author'] if image else '',
        ))
    return replace_rows(Battle, objects, SOURCE)


def _count(text):
    return int(text) if text else None
