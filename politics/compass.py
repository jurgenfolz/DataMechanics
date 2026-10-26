"""The party compass: where expert surveys place a country's parties on an economic and a social axis.

Both axes run from 0 to 10.
The economic axis runs from the left (an active state in the economy) to the right (a smaller state).
The social axis runs from progressive (expanded personal freedoms) to conservative (order, tradition, religion).
Each survey is shown on its own, never averaged with another: their experts, questions and years differ.
A country shows the surveys that place its parties, in the order of SURVEYS.
tools/party_positions.py turns each survey's answers into the two axes.
For Brazil it also infers the places of relevant parties a survey left out, and the page marks them as inferred.
"""

from dataclasses import dataclass

from django.conf import settings
from django.utils.safestring import mark_safe
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


# In the order of the page's dropdown; a country's first survey is its default, because it places the most parties.
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
    'ches-europe': Survey(
        name='CHES Europe',
        years='2024',
        method=_('Political scientists who study the country’s parties placed each party directly on the two axes, from 0 '
                 'to 10, between October and December 2024: one for economic issues such as taxes, privatization and the '
                 'welfare state, one for social and cultural values, from expanded personal freedoms to order and '
                 'tradition. A party’s place is the average of their answers.'),
        citation=('Rovny, J., Polk, J., Bakker, R., Hooghe, L., Jolly, S., Marks, G., Steenbergen, M. and Vachudova, M. A. '
                  '(2025). The 2024 Chapel Hill Expert Survey on political party positioning in Europe.'),
        url='https://www.chesdata.eu/ches-europe',
        licence='',
    ),
    'gps': Survey(
        name='Global Party Survey',
        years='2019',
        method=_('Experts placed each party directly on the two axes, from 0 to 10, with questions much like those of the '
                 'Chapel Hill survey.'),
        citation='Norris, P. (2020). Global Party Survey, 2019. Harvard Dataverse.',
        url='https://doi.org/10.7910/DVN/WMGTNS',
        licence='CC0 1.0',
    ),
}

# What a survey's method needs to add for one country.
SURVEY_NOTES = {
    ('gps', 'BRA'): _('Its own party list leaves out PSD and PL, then called PR, so their places here are the average of '
                      'the experts’ answers, worked out as for the other parties.'),
}

# What a country's page says of it alone: notes to keep in mind beside the general ones, and its credits, as HTML.
CONTEXT = {
    'BRA': {
        'limits': (
            _('<strong>Each survey shows one moment.</strong> PREPPS asked in 2018 and 2019, the Global Party Survey in '
              '2019 and CHES in 2020. Parties have changed since: Bolsonaro joined PL at the end of 2021, and PSL and DEM '
              'merged into União Brasil in 2022.'),
            _('<strong>The surveys do not always agree.</strong> They asked different experts different questions. Switch '
              'the survey to see how far a party moves: PSDB, for one, sits near the centre on the economy in two surveys '
              'and clearly right of it in PREPPS.'),
            _('<strong>Small parties are missing.</strong> Parties with fewer than two deputies and no senator are left out, '
              'and a few parties had few experts placing them: the tooltip says how many.'),
        ),
        'credits': _("Positions: PREPPS Latam, CHES Latin America and the Global Party Survey, as each survey's notes "
                     "describe. Inferred places: Bolognesi, Ribeiro and Codato, a 2018 survey of Brazilian political "
                     "scientists (Harvard Dataverse, CC0). Views: Wikipedia, linked from each party. Logos: Wikimedia "
                     "Commons, all in the public domain."),
    },
    'DEU': {
        'limits': (
            _('<strong>Each survey shows one moment.</strong> The Global Party Survey asked in 2019 and CHES at the end of '
              '2024. Parties have changed since: BSW split from Die Linke in January 2024, so only CHES places it, and the '
              'FDP and BSW left the Bundestag at the February 2025 election.'),
            _('<strong>The surveys do not always agree.</strong> They asked different experts different questions, five '
              'years apart. Switch the survey to see how far a party moves: the AfD, for one, sits further right on the '
              'economy in CHES than in the Global Party Survey.'),
            _('<strong>Small parties are missing.</strong> The chart shows the parties in the Bundestag and those that won '
              'at least 3 percent of the vote in 2025. SSW, the party of the Danish and Frisian minorities, holds a seat '
              'but is in neither survey.'),
        ),
        'credits': _("Positions: CHES Europe and the Global Party Survey, as each survey's notes describe. Views: Wikipedia, "
                     "linked from each party. Logos: Wikimedia Commons."),
    },
    'AUT': {
        'limits': (
            _('<strong>Each survey shows one moment.</strong> The Global Party Survey asked in 2019 and CHES at the end of '
              '2024, after the election of September 2024.'),
            _('<strong>The surveys do not always agree.</strong> They asked different experts different questions, five '
              'years apart. Switch the survey to see how far a party moves: the FPÖ, for one, sits further towards order '
              'and tradition in CHES than in the Global Party Survey.'),
            _('<strong>Small parties are missing.</strong> The chart shows the parties in the Nationalrat.'),
        ),
        'credits': _("Positions: CHES Europe and the Global Party Survey, as each survey's notes describe. Views: Wikipedia, "
                     "linked from each party. Logos: Wikimedia Commons."),
    },
}

# Where Wikipedia puts a party on the left-right spectrum, as written in party_profiles.csv; empty where it gives none.
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
    'Danish minority interests': _('Danish minority interests'),
    'democratic socialism': _('democratic socialism'),
    'developmentalism': _('developmentalism'),
    'direct democracy': _('direct democracy'),
    'eco-feminism': _('eco-feminism'),
    'eco-socialism': _('eco-socialism'),
    'economic liberalism': _('economic liberalism'),
    'environmentalism': _('environmentalism'),
    'Euroscepticism': _('Euroscepticism'),
    'federalism': _('federalism'),
    'Frisian minority interests': _('Frisian minority interests'),
    'green politics': _('green politics'),
    'labourism': _('labourism'),
    'left-conservatism': _('left-conservatism'),
    'left-wing populism': _('left-wing populism'),
    'liberal conservatism': _('liberal conservatism'),
    'liberalism': _('liberalism'),
    'libertarianism': _('libertarianism'),
    'national conservatism': _('national conservatism'),
    'national liberalism': _('national liberalism'),
    'neoliberalism': _('neoliberalism'),
    'parliamentarism': _('parliamentarism'),
    'paternalistic conservatism': _('paternalistic conservatism'),
    'progressivism': _('progressivism'),
    'regionalism': _('regionalism'),
    'right-wing populism': _('right-wing populism'),
    'social conservatism': _('social conservatism'),
    'social democracy': _('social democracy'),
    'social liberalism': _('social liberalism'),
    'socialism': _('socialism'),
    'socialism of the 21st century': _('socialism of the 21st century'),
    'Third Way': _('Third Way'),
    'völkisch nationalism': _('völkisch nationalism'),
}


def has_compass(country):
    return PartyProfile.objects.filter(country=country).exists()


def position_text(position):
    """'centre|centre-right' -> 'Centre to centre-right', in the page's language; '' for a party Wikipedia gives none."""
    if not position:
        return ''  # SSW declines to place itself on the left-right scale, and Wikipedia gives it no position
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
    `context` holds what the page says of this country alone: its notes to keep in mind, and its credits.
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
    method = lambda key: ' '.join(str(text) for text in (SURVEYS[key].method, SURVEY_NOTES.get((key, country.iso3))) if text)
    shown = [key for key in SURVEYS if positions[key]]
    return {
        'fits': fits,
        'surveys': [{'key': key, 'name': SURVEYS[key].name, 'years': SURVEYS[key].years, 'method': method(key),
                     'citation': SURVEYS[key].citation, 'url': SURVEYS[key].url, 'licence': SURVEYS[key].licence}
                    for key in shown],
        'parties': {key: party_info(party) for key, party in parties.items()},
        'positions': {key: positions[key] for key in shown},
        'inferred': any(p['inferred'] for key in shown for p in positions[key]),
        'context': context(country),
    }


def context(country):
    """What the page says of this country alone: its notes to keep in mind, and its credits, as HTML."""
    texts = CONTEXT.get(country.iso3, {'limits': (), 'credits': ''})
    return {'limits': [mark_safe(str(text)) for text in texts['limits']], 'credits': mark_safe(str(texts['credits']))}
