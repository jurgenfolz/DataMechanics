"""What Politics mode measures a country against: the world, or a group of countries.

The page draws the group as a dashed line and gives, for each term, the group's change over the same years.
A group's value in a year is the average of its members.
A year counts only when every member has a value: one member missing would make the line jump.
The world is the source's own World value; a source without one has no world comparison.
A total (GDP, population) has no comparison: a group's total would dwarf the country's, and the two would not compare.
The page may also compare with nothing (NONE): then it looks as it did before groups existed.
"""

from collections import defaultdict
from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _

WORLD = 'WLD'


@dataclass(frozen=True)
class Group:
    label: str
    compared: str  # what the saved images and the reel add to their subtitle
    members: tuple[str, ...] = ()  # ISO 3166-1 alpha-3 codes; empty for the world


# BRICS as it was founded: Brazil, Russia, India and China, with South Africa from 2010, before the 2024 enlargement.
# The G20's 19 member countries; the European Union and the African Union are members too, but not countries.
# Each group has its own "compared with" text: German and Portuguese word them differently ("mit der Welt", "mit den
# G7-Ländern").
GROUPS = {
    'world': Group(_('World'), _('compared with the world')),
    'brics': Group(_('BRICS'), _('compared with BRICS countries'), ('BRA', 'RUS', 'IND', 'CHN', 'ZAF')),
    'g7': Group(_('G7'), _('compared with G7 countries'), ('CAN', 'FRA', 'DEU', 'ITA', 'JPN', 'GBR', 'USA')),
    'g20': Group(_('G20'), _('compared with G20 countries'), ('ARG', 'AUS', 'BRA', 'CAN', 'CHN', 'FRA', 'DEU', 'IND', 'IDN',
                                                             'ITA', 'JPN', 'KOR', 'MEX', 'RUS', 'SAU', 'ZAF', 'TUR', 'GBR',
                                                             'USA')),
}
DEFAULT = 'world'
NONE = 'none'  # the page's choice to compare with nothing


def label(metric, key):
    """The group's name on the page; the world takes the metric's own name for it, e.g. 'World (average of countries)'."""
    return metric.world_label if key == 'world' else GROUPS[key].label


def values(metric, series):
    """Every group's value by year, read in one query: {key: {year: value}}. Empty for a total."""
    if series.total:
        return {}
    members = {key: group.members or (WORLD,) for key, group in GROUPS.items()}
    found = defaultdict(dict)  # a country's values: {year: value}
    rows = (metric.model.objects.filter(country_id__in=set().union(*members.values()))
            .exclude(**{f'{series.field}__isnull': True}).values_list('country_id', 'year', series.field))
    for code, year, value in rows:
        found[code][year] = value
    groups = {}
    for key, codes in members.items():
        years = set.intersection(*(set(found[code]) for code in codes))
        groups[key] = {year: sum(found[code][year] for code in codes) / len(codes) for year in sorted(years)}
    return groups
