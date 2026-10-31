"""The seats in a country's parliament, party by party, house by house: who sits there now, and who sits next.

Each house's provider loads the members in office from the house's own open data, into pol_deputy (lower houses) or
pol_senator (upper houses), one country's rows each: providers/camara/ and providers/senado/ for Brazil,
providers/abgeordnetenwatch/ for Germany, providers/parlament_at/ for Austria, providers/unitedstates/ for the
United States, providers/assemblee_nationale/ and providers/senat/ for France, providers/camera_it/ and
providers/senato_it/ for Italy, providers/uk_parliament/ for the United Kingdom.
providers/tse/ loads the members elected in Brazil's last general election, who take office on 1 February of the next year.
Brazil's senators sit for eight years and half the Senate, roughly, is elected at a time.
So the next Senate is the senators just elected and those whose terms run on, with the party they have today.
The seats run from left to right by each party's score on one left-right scale (politics/spectrum.py).
Parties without a score come after, the largest first.
"""

from collections import Counter
from datetime import date

from django.utils.formats import date_format
from django.utils.safestring import mark_safe
from django.utils.translation import gettext, gettext_lazy as _

from geo.models import EtlLoad

from . import compass, spectrum
from .models import Deputy, Elected, PartyLeftRight, PartyProfile, Senator

NO_PARTY = '#999999'
LEGISLATURE = 4  # years: Brazil's legislature runs from 1 February after an election to 31 January four years on

# Each country's houses, in the order of the page's pills.
# `seats` is the house's full size; its members in office may be fewer for a while.
# `source` is the name its provider logs in etl_load (the provider takes it from here), which gives the source line its
# link and fetch date.
# `term` gives, for a house elected for a fixed term, the day its current term began and how many years a term lasts.
# Brazil's terms come from its last election instead (pol_elected).
HOUSES = {
    'BRA': {
        'chamber': {'model': Deputy, 'name': _('Chamber of Deputies'), 'seats': 513, 'source': 'Câmara dos Deputados, Dados Abertos'},
        'senate': {'model': Senator, 'name': _('Federal Senate'), 'seats': 81, 'source': 'Senado Federal, Dados Abertos'},
    },
    'DEU': {
        'bundestag': {'model': Deputy, 'name': _('Bundestag'), 'seats': 630, 'source': 'abgeordnetenwatch.de',
                      'term': (date(2025, 3, 25), 4)},
    },
    'USA': {
        'house': {'model': Deputy, 'name': _('House of Representatives'), 'seats': 435,
                  'source': 'congress-legislators (@unitedstates)', 'term': (date(2025, 1, 3), 2)},
        'senate': {'model': Senator, 'name': _('Senate'), 'seats': 100, 'source': 'congress-legislators (@unitedstates)'},
    },
    'FRA': {
        'assemblee': {'model': Deputy, 'name': _('National Assembly'), 'seats': 577, 'source': 'Assemblée nationale, Open Data',
                      'term': (date(2024, 7, 18), 5)},
        'senat': {'model': Senator, 'name': _('Senate'), 'seats': 348, 'source': 'Sénat, Open Data'},
    },
    'ITA': {
        'camera': {'model': Deputy, 'name': _('Chamber of Deputies'), 'seats': 400, 'source': 'Camera dei Deputati, Dati aperti',
                   'term': (date(2022, 10, 13), 5)},
        # 200 elected senators and the senators for life, who sit in the groups like everyone else.
        'senato': {'model': Senator, 'name': _('Senate of the Republic'), 'seats': 205, 'source': 'Senato della Repubblica, Dati aperti',
                   'term': (date(2022, 10, 13), 5)},
    },
    'GBR': {
        'commons': {'model': Deputy, 'name': _('House of Commons'), 'seats': 650, 'source': 'UK Parliament, Members API',
                    'term': (date(2024, 7, 9), 5)},
        # The Lords has no fixed size: the half circle shows the members who can sit today.
        'lords': {'model': Senator, 'name': _('House of Lords'), 'seats': None, 'source': 'UK Parliament, Members API'},
    },
    'AUT': {
        'nationalrat': {'model': Deputy, 'name': _('National Council'), 'seats': 183, 'source': 'Parlament Österreich, Open Data',
                        'term': (date(2024, 10, 24), 5)},
        'bundesrat': {'model': Senator, 'name': _('Federal Council'), 'seats': 60, 'source': 'Parlament Österreich, Open Data'},
    },
}

# How each country's page names its parliament: the tab, the card and the images' title. Brazil's is a Congress.
PARLIAMENTS = {
    'BRA': {'tab': _('Congress'), 'card': _('Seats in Congress'), 'title': _('%(name)s’s Congress, party by party')},
    'USA': {'tab': _('Congress'), 'card': _('Seats in Congress'), 'title': _('The %(name)s Congress, party by party')},
    'GBR': {'tab': _('Parliament'), 'card': _('Seats in Parliament'), 'title': _('The %(name)s Parliament, party by party')},
}
ELECTION_SOURCE = 'Tribunal Superior Eleitoral, Dados Abertos'  # Brazil's elected members (providers/tse/)
PARLIAMENT = {'tab': _('Parliament'), 'card': _('Seats in Parliament'), 'title': _('%(name)s’s Parliament, party by party')}

# What a country's page says of it alone, as HTML: a note on its blocs, and its credits.
CONTEXT = {
    'BRA': {
        'blocs': _('In 2022 no party fell in the centre band itself, 4.5 to 5.5. PRD, founded after the survey by PTB and '
                   'Patriota, takes the average of the two; a party founded later has no score.'),
        'credits': _('Seats: the open data of the Câmara dos Deputados, the Senado Federal and the Tribunal Superior '
                     "Eleitoral (CC BY). Left and right: Bolognesi, Codato, Ribeiro and Silva's survey of Brazilian "
                     'political scientists (Harvard Dataverse, CC0), with the bands of Bolognesi, Ribeiro and Codato '
                     '(Dados, 2023).'),
    },
    'DEU': {
        'blocs': _('SSW is not in the survey, so its seat is not classified.'),
        'credits': _('Seats: abgeordnetenwatch.de (CC0). Left and right: the 2024 Chapel Hill Expert Survey (CHES Europe), '
                     'with the bands of Bolognesi, Ribeiro and Codato (Dados, 2023).'),
    },
    'USA': {
        'blocs': _('The Global Party Survey asked no general left-right question about the parties, only an economic and '
                   'a social one, so here a party’s place is its economic one: the left wants the state to play an active '
                   'role in the economy, the right a smaller one. Independents belong to no party, so they are not '
                   'classified.'),
        'credits': _('Seats: the congress-legislators data of the @unitedstates project (public domain, CC0). Left and '
                     'right: the 2019 Global Party Survey (Norris, Harvard Dataverse, CC0), with the bands of Bolognesi, '
                     'Ribeiro and Codato (Dados, 2023).'),
    },
    'FRA': {
        'blocs': _('Seats are counted by parliamentary group, each under its main party: the Assemblée’s EPR under '
                   'Renaissance, the Sénat’s SER under the PS, and so on. So the three UDR senators, who sit in the RN’s '
                   'group, count for the RN. Éric Ciotti’s UDR is not in the survey, nor are LIOT, the RDSE and the Union '
                   'centriste, groups of several small parties, so their seats are not classified. Members in no group '
                   'count as no party.'),
        'credits': _('Seats: the open data of the Assemblée nationale and the Sénat (Licence Ouverte). Left and right: the '
                     '2024 Chapel Hill Expert Survey (CHES Europe), with the bands of Bolognesi, Ribeiro and Codato '
                     '(Dados, 2023).'),
    },
    'ITA': {
        'blocs': _('Seats are counted by parliamentary group, each under its party; in the Camera’s mixed group, by the '
                   'components the Camera names. Italia Viva on its own, Noi Moderati, Futuro Nazionale and Sud chiama Nord '
                   'are not in the survey, nor are the mixed groups and the Senate’s groups Per le Autonomie and Civici '
                   'd’Italia, so their seats are not classified. Alleanza Verdi e Sinistra, the joint list of Europa Verde '
                   'and Sinistra Italiana, takes the average of the two.'),
        'credits': _('Seats: the open data of the Camera dei Deputati (CC BY-SA 4.0) and the Senato della Repubblica (CC BY 3.0); '
                     'the seat counts here are shared under CC BY-SA too. Left and right: the 2024 Chapel Hill Expert Survey '
                     '(CHES Europe), with the bands of Bolognesi, Ribeiro and Codato (Dados, 2023).'),
    },
    'GBR': {
        'blocs': _('CHES scores only the parties of Great Britain, so the seats of the Northern Irish parties, of parties '
                   'too new for the survey and of the Speakers, and in the Lords those of the crossbenchers, the bishops, '
                   'the non-affiliated peers and a Conservative Independent, are not classified. Independents count as no '
                   'party.'),
        'credits': _('Seats: UK Parliament, Members API. Contains Parliamentary information licensed under the '
                     '<a href="https://www.parliament.uk/site-information/copyright-parliament/open-parliament-licence/">Open '
                     'Parliament Licence v3.0</a>. Left and right: the 2024 Chapel Hill Expert Survey (CHES Europe), with '
                     'the bands of Bolognesi, Ribeiro and Codato (Dados, 2023).'),
    },
    'AUT': {
        'blocs': '',
        'credits': _('Seats: the open data of the Austrian Parliament (CC BY 4.0). Left and right: the 2024 Chapel Hill '
                     'Expert Survey (CHES Europe), with the bands of Bolognesi, Ribeiro and Codato (Dados, 2023).'),
    },
}


def has_seats(country):
    return Deputy.objects.filter(country=country).exists() or Senator.objects.filter(country=country).exists()


def parliament(country):
    """How the page names this country's parliament: { tab, card, title }, the title with the country's name in it."""
    names = PARLIAMENTS.get(country.iso3, PARLIAMENT)
    return {'tab': str(names['tab']), 'card': str(names['card']), 'title': str(names['title']) % {'name': country.local_name}}


def data(country):
    """Each house's parties with their seats, today and after the election, and where the numbers come from."""
    # A party's code in each house's data; two houses may code it differently (France's PS is SOC in the Assemblée,
    # SER in the Sénat), so a profile can hold several codes, ';'-separated.
    profiles = {code.casefold(): profile for profile in PartyProfile.objects.filter(country=country)
                for code in profile.congress.split(';') if code}
    scores = {row.party_id: row for row in PartyLeftRight.objects.filter(party__country=country)}
    seats = lambda codes: order([party_seats(code, n, profiles.get(code.casefold()), scores) for code, n in Counter(codes).items()])
    elected = Elected.objects.filter(country=country)
    first = elected.order_by('elected_on').first()
    # The elected take office on 1 February after the election; from then on, the houses' own data has them.
    starts = date(first.elected_on.year + 1, 2, 1) if first else None
    upcoming = bool(starts) and date.today() < starts
    houses = []
    for key, house in HOUSES.get(country.iso3, {}).items():
        members = house['model'].objects.filter(country=country)
        if not members.exists():
            continue
        today = source(house['model'], house['source'])
        today['note'] = gettext('members in office on %(date)s') % {'date': today['fetched']}
        if 'term' in house:
            now = fixed_term(*house['term'])
        else:
            # Before the elected take office, today's seats belong to the legislature that ends as theirs begins.
            now = period(date(starts.year - LEGISLATURE, 2, 1) if upcoming else starts)
        terms = [{'key': 'now', 'label': gettext('Today'), 'parties': seats(members.values_list('party', flat=True)),
                  'sources': [today], 'period': now}]
        if upcoming:
            terms.append(next_term(key, members, elected.filter(house=key), first.elected_on, starts, seats))
        for term in terms:
            term['members'] = sum(party['seats'] for party in term['parties'])
        houses.append({'key': key, 'name': str(house['name']), 'seats': house['seats'], 'terms': terms})
    texts = CONTEXT.get(country.iso3, {'blocs': '', 'credits': ''})
    return {
        'houses': houses,
        'starts': date_format(starts) if upcoming else '',
        'blocs': spectrum.blocs(),
        'spectrum': spectrum.SURVEYS.get(country.iso3),
        'parliament': parliament(country),
        # The credits are the site's own text and may hold a link, as a licence can ask.
        'context': {'blocs': str(texts['blocs']), 'credits': mark_safe(str(texts['credits']))},
    }


def next_term(key, members, elected, elected_on, starts, seats):
    """A house as the election left it: the members just elected and, in the Senate, the senators whose terms run on."""
    day = date_format(elected_on)
    won = source(Elected, ELECTION_SOURCE)
    won['note'] = gettext('elected on %(day)s') % {'day': day}
    codes, sources = list(elected.values_list('party', flat=True)), [won]
    if key == 'senate':
        staying = members.filter(term_ends__gt=starts.year)
        codes += list(staying.values_list('party', flat=True))
        won['note'] = gettext('%(count)s elected on %(day)s') % {'count': elected.count(), 'day': day}
        stay = source(Senator, HOUSES['BRA']['senate']['source'])
        stay['note'] = gettext('%(count)s whose terms run on, with their party on %(date)s') % {
            'count': staying.count(), 'date': stay['fetched']}
        sources.append(stay)
    return {'key': 'next', 'label': gettext('From %(year)s') % {'year': starts.year}, 'parties': seats(codes), 'sources': sources,
            'period': period(starts)}


def fixed_term(start, years):
    """A term that began on `start` and runs `years` at most, for the page: its first day and its years; it has no set last day."""
    return {'from': date_format(start), 'to': '', 'years': f'{start.year}–{start.year + years}'}


def period(start):
    """Brazil's legislature that begins on `start`, for the page: its first and last days, and its years; None when unknown."""
    if not start:
        return None
    end = date(start.year + LEGISLATURE, 1, 31)
    return {'from': date_format(start), 'to': date_format(end), 'years': f'{start.year}–{end.year}'}


def source(model, name):
    """Where a house's rows come from, and when we fetched them: the latest load of `model`'s table from source `name`."""
    load = EtlLoad.objects.filter(table_name=model._meta.db_table, source_name=name).first()
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
