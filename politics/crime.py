"""Crime suspects by nationality, for a Politics page tab: the share of each nationality's people whom the police registered as suspects.

The suspects come from the police crime statistics, the people from the population statistics (SOURCES).
The page counts suspects of every offence but those against residence and asylum law: only foreigners can break those laws.
Its picker chooses the kinds of offence (OFFENCES), from the police statistics' own groups.
tools/germany_suspects.py builds the data; providers/curated/population_by_nationality.py and suspects.py load it.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from django.conf import settings
from django.utils.formats import date_format, number_format
from django.utils.translation import gettext, gettext_lazy as _

from geo.models import EtlLoad
from metrics.formatting import format_value
from metrics.queries import flag_url

from .models import NationalityPopulation, Suspects

# A nationality with fewer people in the country is left out: with so few, a handful of suspects moves its share a lot.
# The Solomon Islands had 5 people in Germany's register in 2025, and 8 suspects.
MIN_PEOPLE = 10_000

# The chart opens with the country's citizens and the foreign nationalities with the highest shares, this many of them.
HIGHEST = 20

EVERY = '------'  # the police statistics' key for every offence, residence and asylum law included
TOTAL = '890000'  # every offence but those against residence and asylum law


@dataclass(frozen=True)
class Offence:
    """A kind of offence as the police statistics group them, with the kinds inside it."""

    key: str  # the PKS key: six digits, with * for any digit in the theft keys
    name: str
    children: tuple = ()
    summed: bool = False  # its own count cannot be used, so it counts as the sum of its children


def kind(key, name, *children, summed=False):
    return Offence(key, name, children, summed)


# The kinds of offence the page can choose. The German names are the BKA's, without their sections of the law.
# Theft has no group key of its own: ****00 is the BKA's sum of simple theft (3***00) and aggravated theft (4***00).
# Offences under other laws (700000) take in residence and asylum law (725000, inside 720000).
# So here they are the sum of the other laws' groups.
# The smallest of those are left out: youth protection, passports, cultural goods and data protection (721000, 722000,
# 724000, 727000 and 728000), 731 suspects in 2025.
OFFENCES = kind(TOTAL, _('Total'),
    kind('000000', _('Offences against life'),
         kind('010000', _('Murder')),
         kind('020000', _('Manslaughter and killing on request')),
         kind('030000', _('Negligent homicide, outside road accidents')),
         kind('040000', _('Illegal abortion'))),
    kind('100000', _('Sexual offences'),
         kind('110000', _('Rape, sexual assault and sexual harassment')),
         kind('130000', _('Sexual abuse')),
         kind('140000', _('Sexual exploitation, pimping and pornography'))),
    kind('200000', _('Robbery, bodily harm and offences against personal liberty'),
         kind('210000', _('Robbery')),
         kind('220000', _('Bodily harm')),
         kind('230000', _('Offences against personal liberty, such as threats and stalking'))),
    kind('****00', _('Theft'),
         kind('3***00', _('Simple theft')),
         kind('4***00', _('Aggravated theft, such as burglary'))),
    kind('500000', _('Property and forgery offences'),
         kind('510000', _('Fraud')),
         kind('520000', _('Breach of trust')),
         kind('530000', _('Misappropriation')),
         kind('540000', _('Forgery of documents')),
         kind('550000', _('Counterfeiting money and payment cards')),
         kind('560000', _('Insolvency offences'))),
    kind('600000', _('Other offences under the Criminal Code'),
         kind('610000', _('Extortion')),
         kind('620000', _('Resisting or attacking officers, and offences against public order')),
         kind('630000', _('Handling stolen goods, money laundering and obstructing justice')),
         kind('640000', _('Arson')),
         kind('650000', _('Corruption, bid rigging and offences in office')),
         kind('660000', _('Illegal gambling, usury and poaching')),
         kind('670000', _('All other Criminal Code offences, such as insult and criminal damage'))),
    kind('700000', _('Offences under other laws, without residence and asylum law'),
         kind('710000', _('Economic laws')),
         kind('726000', _('Weapons and explosives laws')),
         kind('730000', _('Drug offences')),
         kind('740000', _('Environmental and consumer protection laws')),
         summed=True),
)

# Where each country's numbers come from, with the date each source gives its table (None where it gives none).
SOURCES = {
    'DEU': [
        {'name': 'Bundeskriminalamt, Polizeiliche Kriminalstatistik 2025, T62',
         'url': ('https://www.bka.de/DE/AktuelleInformationen/StatistikenLagebilder/PolizeilicheKriminalstatistik/PKS2025/'
                 'pksTabellen_Interpretationshilfen/BundTVNationalitaet/bundTVNationalitaet.html'),
         'updated': date(2026, 2, 19)},
        {'name': 'Statistisches Bundesamt (Destatis), Ausländerzentralregister, 12521-0002',
         'url': 'https://genesis.destatis.de/datenbank/online/statistic/12521/table/12521-0002',
         'updated': date(2026, 10, 27)},
        {'name': 'Statistisches Bundesamt (Destatis), Bevölkerungsfortschreibung',
         'url': ('https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/Bevoelkerungsstand/Tabellen/'
                 'zensus-geschlecht-staatsangehoerigkeit-2025.html'),
         'updated': None},
    ],
}

# What a country's page says of its numbers alone: the label of its people, how they are counted, and who the police
# count beyond them. `limits` closes the video: what the shares cannot show.
CONTEXT = {
    'DEU': {
        'population': _('Population in Germany'),
        'limits': _('A suspect is not a convict. Three in four suspects are men, and the share of men differs between '
                    'nationalities; the shares are not adjusted for age or sex. The police also count some people who do not '
                    'live in Germany.'),
        'notes': [
            _('Foreign nationals are counted by the Central Register of Foreigners: 14.1 million on 31 December 2025. '
              'The population update on the 2022 census counts 12.4 million; the two count in different ways. '
              'Germans are counted by the population update.'),
            _('The police count every suspect: in 2025 also 6,390 foreign nationals who do not live in Germany and '
              '23,923 who stayed without permission (BKA table T61). The register counts only people who live here, '
              "so they raise the shares a little. The BKA's own rates leave out suspects who do not live in Germany."),
            _('Three in four suspects are men (T61). Among the foreign nationals in the register, 52% are men; among '
              'Germans, 49%. The police table gives no ages or sexes by nationality, so the shares cannot be '
              'adjusted for either.'),
        ],
    },
}


def has_suspects(country):
    """Whether the page shows the Crime tab: the country has the data, and the tab is switched on (settings.CRIME_TAB)."""
    return settings.CRIME_TAB and Suspects.objects.filter(country=country).exists()


def counted(offence=OFFENCES):
    """The keys whose counts the page uses: every kind of offence but those summed from their children, and EVERY."""
    keys = [] if offence.summed else [offence.key]
    for child in offence.children:
        keys += counted(child)
    return keys + ([EVERY] if offence is OFFENCES else [])


def tree(offence=OFFENCES):
    """A kind of offence for the page's picker, named in the page's language, with the kinds inside it."""
    return {'key': offence.key, 'name': str(offence.name), 'summed': offence.summed,
            'children': [tree(child) for child in offence.children]}


def data(country):
    """Each nationality's people and suspects, by kind of offence, in the latest year, and the sources.

    Only nationalities with MIN_PEOPLE people or more are listed; the country's own citizens are among them.
    `own` is the code of the country's own citizens; `foreign` is every foreign national together.
    A nationality's `suspects` maps a kind of offence's key to its suspects; a kind missing from it had none.
    """
    people = list(NationalityPopulation.objects.filter(country=country).select_related('nationality'))
    year = max(row.year for row in people)
    people = [row for row in people if row.year == year]
    suspects = defaultdict(dict)
    for row in Suspects.objects.filter(country=country, year=year):
        suspects[row.nationality_id][row.offence] = row.suspects
    foreign = next(row for row in people if row.nationality is None)
    load = EtlLoad.objects.filter(table_name=Suspects._meta.db_table).first()
    share = lambda part, whole: format_value(part / whole * 100, 'percent')
    context = CONTEXT.get(country.iso3, {})
    return {
        'year': year,
        'own': country.iso2,
        'highest': HIGHEST,
        'offences': tree(),
        'nationalities': [nationality(row, suspects[row.nationality_id]) for row in people
                          if row.nationality and row.population >= MIN_PEOPLE],
        'foreign': {'population': foreign.population, 'suspects': suspects[None]},
        'sources': [{'name': source['name'], 'url': source['url'],
                     'updated': date_format(source['updated']) if source['updated'] else ''}
                    for source in SOURCES.get(country.iso3, [])],
        'loaded': date_format(load.loaded_at, 'SHORT_DATE_FORMAT') if load else '',
        # The note on residence and asylum law, with its numbers written in the page's language.
        'text': {
            'foreign': share(suspects[None].get(TOTAL, 0), foreign.population),
            'foreignAll': share(suspects[None].get(EVERY, 0), foreign.population),
            'floor': number_format(MIN_PEOPLE, force_grouping=True),
        },
        'population': str(context.get('population', gettext('Population'))),
        'limits': str(context.get('limits', '')),
        'notes': [str(note) for note in context.get('notes', [])],
    }


def nationality(row, suspects):
    """One nationality as the chart and its table show it, named in the page's language."""
    country = row.nationality
    return {'code': country.iso2 or country.iso3.lower(), 'name': country.local_name, 'flag': flag_url(country.iso3, country.iso2),
            'population': row.population, 'suspects': suspects}


def title(country):
    """The title of the chart's images and videos, with the country's name in it."""
    return gettext('%(name)s: crime suspects by nationality') % {'name': country.local_name}
