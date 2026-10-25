"""The seats in a country's parliament, party by party, house by house: who sits there now, and who sits next.

The providers in providers/camara/ and providers/senado/ load the members in office from each house's open data.
providers/tse/ loads the members elected in the last general election, who take office on 1 February of the next year.
Senators sit for eight years and half the Senate, roughly, is elected at a time.
So the next Senate is the senators just elected and those whose terms run on, with the party they have today.
The seats run from left to right by each party's score on one left-right scale (politics/spectrum.py).
Parties without a score come after, the largest first.
"""

from collections import Counter
from datetime import date

from django.utils.formats import date_format
from django.utils.translation import gettext, gettext_lazy as _

from geo.models import EtlLoad

from . import compass, spectrum
from .models import Deputy, Elected, PartyLeftRight, PartyProfile, Senator

NO_PARTY = '#999999'
LEGISLATURE = 4  # years: a legislature runs from 1 February after an election to 31 January four years on

# In the order of the page's pills. `seats` is the house's full size; its members in office may be fewer for a while.
HOUSES = {
    'chamber': {'model': Deputy, 'name': _('Chamber of Deputies'), 'seats': 513},
    'senate': {'model': Senator, 'name': _('Federal Senate'), 'seats': 81},
}


def has_seats(country):
    return Deputy.objects.filter(country=country).exists() or Senator.objects.filter(country=country).exists()


def data(country):
    """Each house's parties with their seats, today and after the election, and where the numbers come from."""
    profiles = {profile.congress.casefold(): profile for profile in PartyProfile.objects.filter(country=country) if profile.congress}
    scores = {row.party_id: row for row in PartyLeftRight.objects.filter(party__country=country)}
    seats = lambda codes: order([party_seats(code, n, profiles.get(code.casefold()), scores) for code, n in Counter(codes).items()])
    elected = Elected.objects.filter(country=country)
    first = elected.order_by('elected_on').first()
    # The elected take office on 1 February after the election; from then on, the houses' own data has them.
    starts = date(first.elected_on.year + 1, 2, 1) if first else None
    upcoming = bool(starts) and date.today() < starts
    houses = []
    for key, house in HOUSES.items():
        members = house['model'].objects.filter(country=country)
        if not members.exists():
            continue
        today = source(house['model'])
        today['note'] = gettext('members in office on %(date)s') % {'date': today['fetched']}
        # Before the elected take office, today's seats belong to the legislature that ends as theirs begins.
        now = date(starts.year - LEGISLATURE, 2, 1) if upcoming else starts
        terms = [{'key': 'now', 'label': gettext('Today'), 'parties': seats(members.values_list('party', flat=True)),
                  'sources': [today], 'period': period(now)}]
        if upcoming:
            terms.append(next_term(key, members, elected.filter(house=key), first.elected_on, starts, seats))
        for term in terms:
            term['members'] = sum(party['seats'] for party in term['parties'])
        houses.append({'key': key, 'name': str(house['name']), 'seats': house['seats'], 'terms': terms})
    return {
        'houses': houses,
        'starts': date_format(starts) if upcoming else '',
        'blocs': spectrum.blocs(),
        'spectrum': spectrum.SURVEY,
    }


def next_term(key, members, elected, elected_on, starts, seats):
    """A house as the election left it: the members just elected and, in the Senate, the senators whose terms run on."""
    day = date_format(elected_on)
    won = source(Elected)
    won['note'] = gettext('elected on %(day)s') % {'day': day}
    codes, sources = list(elected.values_list('party', flat=True)), [won]
    if key == 'senate':
        staying = members.filter(term_ends__gt=starts.year)
        codes += list(staying.values_list('party', flat=True))
        won['note'] = gettext('%(count)s elected on %(day)s') % {'count': elected.count(), 'day': day}
        stay = source(Senator)
        stay['note'] = gettext('%(count)s whose terms run on, with their party on %(date)s') % {
            'count': staying.count(), 'date': stay['fetched']}
        sources.append(stay)
    return {'key': 'next', 'label': gettext('From %(year)s') % {'year': starts.year}, 'parties': seats(codes), 'sources': sources,
            'period': period(starts)}


def period(start):
    """The legislature that begins on `start`, for the page: its first and last days, and its years; None when unknown."""
    if not start:
        return None
    end = date(start.year + LEGISLATURE, 1, 31)
    return {'from': date_format(start), 'to': date_format(end), 'years': f'{start.year}–{end.year}'}


def source(model):
    """Where a table's rows come from, and when we fetched them."""
    load = EtlLoad.objects.filter(table_name=model._meta.db_table).first()
    if not load:
        return {'name': '', 'url': '', 'fetched': ''}
    return {'name': load.source_name, 'url': load.source_url, 'fetched': date_format(load.loaded_at, 'SHORT_DATE_FORMAT')}


def order(parties):
    """The parties in their order round the half circle: by left-right score, then those without one, the largest first."""
    placed = sorted((p for p in parties if p['score'] is not None), key=lambda p: p['score'])
    unplaced = sorted((p for p in parties if p['score'] is None), key=lambda p: (-p['seats'], p['abbreviation']))
    return placed + unplaced


def party_seats(code, seats, profile, scores):
    """A party's seats, with what the half circle and its table show of it, and its place on the left-right scale."""
    if profile:
        info = compass.party_info(profile)
        return {'code': code, 'key': profile.key, 'abbreviation': info['abbreviation'], 'name': info['name'],
                'logo': info['logo'], 'logoOnDark': info['logoOnDark'], 'color': info['color'], 'seats': seats,
                **spectrum.classify(scores.get(profile.pk))}
    # A member without a party, or a party not yet in party_profiles.csv: its code, in grey.
    name = gettext('No party') if not code else code
    return {'code': code, 'key': '', 'abbreviation': name, 'name': name, 'logo': '', 'logoOnDark': '', 'color': NO_PARTY,
            'seats': seats, **spectrum.classify(None)}
