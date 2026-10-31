"""The members of the United States Congress, from the @unitedstates project's congress-legislators data (CC0).

The project keeps one file of every member in office, with each member's terms; the last term is the current one.
It is in the public domain: the project waives its rights worldwide under CC0 1.0.
Members count for the party their current term gives: Democrat, Republican or Independent.
"""

from datetime import date

from providers import http

URL = 'https://unitedstates.github.io/congress-legislators/legislators-current.json'
PAGE = 'https://github.com/unitedstates/congress-legislators'
# The House's six non-voting members: the delegates of the District of Columbia and four territories, and Puerto Rico's
# resident commissioner. They are not among its 435 seats.
NON_VOTING = {'AS', 'DC', 'GU', 'MP', 'PR', 'VI'}


def members(kind):
    """The members in office whose current term is of `kind`, 'rep' or 'sen': (member, current term) pairs.

    The file holds only members serving now, so a term's end date is not checked: an appointed senator's term ends on the
    expected date of the special election, and the project corrects it only once the successor is sworn in.
    A term that has not begun yet (a member-elect) is left out.
    """
    today = date.today().isoformat()
    for member in http.get_json(URL):
        term = member['terms'][-1]
        if term['type'] == kind and term['start'] <= today:
            yield member, term


def check(rows, seats):
    """Refuses a load that would leave a house far below its size, e.g. a file caught mid-update after an election."""
    if len(rows) < seats * 0.9:
        raise RuntimeError(f'Only {len(rows)} members of {seats} seats: not loaded.')


def name(member):
    names = member['name']
    return names.get('official_full') or f"{names['first']} {names['last']}"
