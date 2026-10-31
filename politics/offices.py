"""The office a country's Politics page follows, and the words the page uses for it.

Brazil, France and the United States follow their presidents. Germany and Austria follow their chancellors, and Italy and
the United Kingdom their prime ministers, because their heads of state have little power.
German and Portuguese need whole sentences per office, so each office has its own strings.
"""

from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _, ngettext_lazy


@dataclass(frozen=True)
class Office:
    title: str  # the page's title, with %(name)s for the country
    lead: str  # the line under the country's name, with %(year)s for the first year
    by_leader: str  # the view that ranks the leaders
    subtitle: str  # the saved images' subtitle, with %(name)s for the country
    count: str  # the Politics index card, with %(count)s leaders since %(year)s


OFFICES = {
    'president': Office(
        title=_('%(name)s by president'),
        lead=_('Every metric we have, president by president, since %(year)s.'),
        by_leader=_('By president'),
        subtitle=_('%(name)s, president by president'),
        count=ngettext_lazy('%(count)s president since %(year)s', '%(count)s presidents since %(year)s', 'count'),
    ),
    'chancellor': Office(
        title=_('%(name)s by chancellor'),
        lead=_('Every metric we have, chancellor by chancellor, since %(year)s.'),
        by_leader=_('By chancellor'),
        subtitle=_('%(name)s, chancellor by chancellor'),
        count=ngettext_lazy('%(count)s chancellor since %(year)s', '%(count)s chancellors since %(year)s', 'count'),
    ),
    'prime-minister': Office(
        title=_('%(name)s by prime minister'),
        lead=_('Every metric we have, prime minister by prime minister, since %(year)s.'),
        by_leader=_('By prime minister'),
        subtitle=_('%(name)s, prime minister by prime minister'),
        count=ngettext_lazy('%(count)s prime minister since %(year)s', '%(count)s prime ministers since %(year)s', 'count'),
    ),
}


@dataclass(frozen=True)
class Role:
    office: str | None  # None: the role holds no one's office, like a military junta
    label: str = ''  # how the page names the role; empty for the office itself, which the page already names
    acting: bool = False  # an acting leader stands in: the count of a country's leaders leaves them out


# Roles as written in data/politics/<country>/administrations.csv.
ROLES = {
    'President': Role('president'),
    'Acting president': Role('president', _('Acting president'), acting=True),
    'President (military rule)': Role('president', _('President (military rule)')),
    'Military junta': Role(None, _('Military junta')),
    'Chancellor': Role('chancellor'),
    'Acting chancellor': Role('chancellor', _('Acting chancellor'), acting=True),
    'Prime minister': Role('prime-minister'),
    'Acting prime minister': Role('prime-minister', _('Acting prime minister'), acting=True),
}


def office_key(tenures):
    """The office a country's page follows: the one its current leader holds."""
    return ROLES[tenures[-1].role].office


def office_of(tenures):
    return OFFICES[office_key(tenures)]
