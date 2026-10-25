"""The party compass: where expert surveys place a country's parties on an economic and a social axis.

Both axes run from 0 to 10.
The economic axis runs from the left (an active state in the economy) to the right (a smaller state).
The social axis runs from progressive (expanded personal freedoms) to conservative (order, tradition, religion).
Each survey is shown on its own, never averaged with another: their experts, questions and years differ.
tools/party_positions.py turns each survey's answers into the two axes.
It also infers the places of relevant parties a survey left out, and the page marks them as inferred.
"""

from dataclasses import dataclass

from django.conf import settings
from django.utils.translation import gettext, gettext_lazy as _

from .models import PartyPosition, PartyProfile


@dataclass(frozen=True)
class Survey:
    name: str
    years: str
    method: str  # how its answers became the two axes, in simple words
    citation: str
    url: str
    licence: str  # empty when the survey states none


# In the order of the page's dropdown; the first is the default, because it places the most parties.
SURVEYS = {
    'prepps': Survey(
        name='PREPPS Latam',
        years='2018–2019',
        method=_('Experts on Brazilian politics rated each party on single issues, from 1 to 20. '
                 'The economic axis here is the average of four of them: taxes and spending, privatization, deregulation '
                 'and redistribution. The social axis is the average of four others: abortion and other moral questions, '
                 'religion in politics, minority rights, and civil liberties against tough measures on crime. '
                 'Both were then stretched from 1–20 to 0–10.'),
        citation='Wiesehomeier, N., Singer, M. M. and Ruth-Lovell, S. (2022). PREPPS Latam V3. Harvard Dataverse.',
        url='https://doi.org/10.7910/DVN/TYVFC3',
        licence='CC0 1.0',
    ),
    'ches': Survey(
        name='CHES Latin America',
        years='2020',
        method=_('Experts on Brazilian politics placed each party directly on the two axes, from 0 to 10: one for economic '
                 'issues such as taxes, privatization and the welfare state, one for social and cultural values such as '
                 'abortion, same-sex marriage and order and tradition.'),
        citation=('Martínez-Gallardo, C., de la Cerda, N., Hartlyn, J., Hooghe, L., Marks, G. and Bakker, R. (2022). '
                  'Revisiting party system structuration in Latin America and Europe. Party Politics.'),
        url='https://www.chesdata.eu/ches-la/',
        licence='',
    ),
    'gps': Survey(
        name='Global Party Survey',
        years='2019',
        method=_('Experts on Brazilian politics placed each party directly on the two axes, from 0 to 10, with questions '
                 'much like those of the Chapel Hill survey. Its own party list leaves out PSD and PL, then called PR, so '
                 'their places here are the average of the experts’ answers, worked out as for the other parties.'),
        citation='Norris, P. (2020). Global Party Survey, 2019. Harvard Dataverse.',
        url='https://doi.org/10.7910/DVN/WMGTNS',
        licence='CC0 1.0',
    ),
}
DEFAULT = next(iter(SURVEYS))

# Where Wikipedia puts a party on the left-right spectrum, as written in party_profiles.csv.
POSITIONS = {
    'far-left': _('far-left'),
    'left-wing': _('left-wing'),
    'centre-left': _('centre-left'),
    'centre': _('centre'),
    'centre-right': _('centre-right'),
    'right-wing': _('right-wing'),
    'far-right': _('far-right'),
}

# The ideologies Wikipedia names for the parties, as written in party_profiles.csv.
IDEOLOGIES = {
    'anti-corruption': _('anti-corruption'),
    'big tent': _('big tent'),
    'Bolsonarism': _('Bolsonarism'),
    'Brazilian nationalism': _('Brazilian nationalism'),
    'Catholic social teaching': _('Catholic social teaching'),
    'Christian democracy': _('Christian democracy'),
    'Christian right': _('Christian right'),
    'Christian solidarism': _('Christian solidarism'),
    'classical liberalism': _('classical liberalism'),
    'communism': _('communism'),
    'conservatism': _('conservatism'),
    'conservative liberalism': _('conservative liberalism'),
    'democratic socialism': _('democratic socialism'),
    'developmentalism': _('developmentalism'),
    'direct democracy': _('direct democracy'),
    'eco-socialism': _('eco-socialism'),
    'economic liberalism': _('economic liberalism'),
    'environmentalism': _('environmentalism'),
    'federalism': _('federalism'),
    'green politics': _('green politics'),
    'labourism': _('labourism'),
    'liberal conservatism': _('liberal conservatism'),
    'libertarianism': _('libertarianism'),
    'national conservatism': _('national conservatism'),
    'national liberalism': _('national liberalism'),
    'neoliberalism': _('neoliberalism'),
    'parliamentarism': _('parliamentarism'),
    'paternalistic conservatism': _('paternalistic conservatism'),
    'progressivism': _('progressivism'),
    'right-wing populism': _('right-wing populism'),
    'social conservatism': _('social conservatism'),
    'social democracy': _('social democracy'),
    'social liberalism': _('social liberalism'),
    'socialism of the 21st century': _('socialism of the 21st century'),
    'Third Way': _('Third Way'),
}


def has_compass(country):
    return PartyProfile.objects.filter(country=country).exists()


def position_text(position):
    """'centre|centre-right' -> 'Centre to centre-right', in the page's language."""
    ends = [str(POSITIONS[end]) for end in position.split('|')]
    text = gettext('%(from)s to %(to)s') % {'from': ends[0], 'to': ends[1]} if len(ends) == 2 else ends[0]
    return text[:1].upper() + text[1:]


def party_info(party):
    """What the compass and the seats show of a party: its names, logo, colour and how Wikipedia describes it."""
    return {
        'abbreviation': party.abbreviation,
        'name': party.name,  # the party's own name: party names are never translated
        'logo': f'{settings.MEDIA_URL}{party.logo}' if party.logo else '',
        # On the dark compass, a logo whose own ink is too dark uses its light-ink copy.
        'logoOnDark': f'{settings.MEDIA_URL}{party.logo_on_dark}' if party.logo_on_dark else '',
        'color': party.color,
        'position': position_text(party.position),
        'ideologies': [str(IDEOLOGIES[term]) for term in party.ideologies.split(';')],
        'viewsSource': party.views_source,
        'ended': gettext('Merged into %(party)s in %(year)s.') % {'party': party.merged_into, 'year': party.ended_year}
        if party.merged_into else '',
        'credit': '' if party.logo_licence == 'Public domain' else f'{party.abbreviation}: {party.logo_author}, {party.logo_licence}',
    }


def inferred_note(position):
    """How an inferred place was estimated, for the tooltip; empty for a survey's own place."""
    if position.inferred == 'merger':
        return gettext('Inferred, not measured: the average of %(parties)s, which merged into it.') % {
            'parties': position.inferred_from}
    if position.inferred == 'scale':
        return gettext('Inferred, not measured: estimated from where %(experts)s political scientists put it on one '
                       'left-right scale in 2018.') % {'experts': position.experts}
    return ''


def data(country):
    """Everything the compass draws: the surveys, the parties and each survey's positions, measured or inferred.

    `fits` gives, for each survey, how well the 2018 left-right scale predicts its own places (R², 0 to 1).
    """
    parties = {party.key: party for party in PartyProfile.objects.filter(country=country)}
    positions = {key: [] for key in SURVEYS}
    fits = {}
    for position in PartyPosition.objects.filter(party__country=country).select_related('party'):
        positions[position.survey].append({
            'party': position.party.key,
            'economic': round(position.economic, 2),
            'social': round(position.social, 2),
            'experts': position.experts,
            'then': gettext('Called %(name)s when this survey asked.') % {'name': position.name_at_survey}
            if position.name_at_survey else '',
            'inferred': position.inferred,
            'note': inferred_note(position),
        })
        if position.economic_fit is not None:
            fits[position.survey] = {'economic': position.economic_fit, 'social': position.social_fit}
    return {
        'fits': fits,
        'surveys': [{'key': key, 'name': survey.name, 'years': survey.years, 'method': str(survey.method),
                     'citation': survey.citation, 'url': survey.url, 'licence': survey.licence}
                    for key, survey in SURVEYS.items()],
        'parties': {key: party_info(party) for key, party in parties.items()},
        'positions': positions,
    }
