"""The UK Parliament's Members API (members-api.parliament.uk), under the Open Parliament Licence v3.0.

The licence asks for this statement: "Contains Parliamentary information licensed under the Open Parliament Licence v3.0."
A member counts for their party as Parliament records it today (`latestParty`), which follows the whip: an MP whose whip
is withdrawn sits as an independent until it is restored. In the Lords the same field gives the party or group:
Crossbench, Bishops, Non-affiliated, Lord Speaker, Conservative Independent. A seat's code is the party's abbreviation, the same in both houses, so Labour and
Labour (Co-op) MPs both count as "Lab"; a group without an abbreviation uses its name. Independents count as no party.
The API returns at most 20 members a request.
"""

from providers import http

SEARCH = 'https://members-api.parliament.uk/api/Members/Search?House={house}&IsCurrentMember=true{extra}&skip={skip}&take={take}'
PAGE_URL = 'https://members-api.parliament.uk/'
TAKE = 20  # the API's largest page
INDEPENDENT = 'Ind'


def party_code(party):
    """'Lab' for Labour and Labour (Co-op) alike; the group's name where it has no abbreviation; '' for an independent."""
    party = party or {}
    code = (party.get('abbreviation') or party.get('name') or '').strip()
    return '' if code == INDEPENDENT else code


def members(house, extra=''):
    """Every current member of one house (1 Commons, 2 Lords) as (member_id, name, party_code)."""
    rows, skip, seen = [], 0, set()
    while True:
        page = http.get_json(SEARCH.format(house=house, extra=extra, skip=skip, take=TAKE))
        for item in page['items']:
            member = item['value']
            if member['id'] not in seen:  # a list that changes while we page could repeat a member
                seen.add(member['id'])
                rows.append((str(member['id']), member['nameDisplayAs'], party_code(member['latestParty'])))
        skip += TAKE
        if skip >= page['totalResults'] or not page['items']:
            return rows
