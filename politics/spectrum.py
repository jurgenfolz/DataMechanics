"""Left, centre and right: where political scientists place a country's parties on one left-right scale.

The scale runs from 0, the far left, to 10, the far right.
The scores come from a 2022 survey of Brazilian political scientists (Bolognesi, Codato, Ribeiro and Silva), loaded by
providers/curated/party_left_right.py.
The survey's authors cut the scale into seven bands, from the far left to the far right (Bolognesi, Ribeiro and Codato,
Dados, 2023).
The page joins the bands into three blocs: the left (far left and left), the centre (centre-left, centre and
centre-right) and the right (right and far right).
"""

from django.utils.translation import gettext_lazy as _

from . import compass

SURVEY = {
    'experts': 571,
    'year': 2022,
    'citation': ('Bolognesi, B., Codato, A., Ribeiro, E. and Silva, B. F. (2025). Database on the ideological '
                 'classification of all Brazilian political parties (2018–2022). Harvard Dataverse.'),
    'url': 'https://doi.org/10.7910/DVN/MFIXKW',
    'bands': ('Bolognesi, B., Ribeiro, E. and Codato, A. (2023). Uma Nova Classificação Ideológica dos Partidos '
              'Políticos Brasileiros. Dados, 66(2).'),
    'bands_url': 'https://doi.org/10.1590/dados.2023.66.2.303',
}

# The authors' seven bands, by the highest mean score in each (two decimals), and the bloc each joins.
# Their keys are those of compass.POSITIONS, which names them in the page's language.
BANDS = (
    (1.50, 'far-left', 'left'),
    (3.00, 'left-wing', 'left'),
    (4.49, 'centre-left', 'centre'),
    (5.50, 'centre', 'centre'),
    (7.00, 'centre-right', 'centre'),
    (8.50, 'right-wing', 'right'),
    (10.00, 'far-right', 'right'),
)

# In the order of the half circle. A party without a score is not classified.
BLOCS = {
    'left': {'name': _('Left'), 'bands': _('far left and left'), 'color': '#e2504c'},
    'centre': {'name': _('Centre'), 'bands': _('centre-left to centre-right'), 'color': '#b0b3b8'},
    'right': {'name': _('Right'), 'bands': _('right and far right'), 'color': '#3d8bfd'},
    'none': {'name': _('Not classified'), 'bands': _('no score in the survey'), 'color': '#5f6368'},
}


def band(score):
    """The authors' band for a mean score: (its key in compass.POSITIONS, the bloc it joins)."""
    rounded = round(score, 2)
    return next((key, bloc) for top, key, bloc in BANDS if rounded <= top)


def classify(left_right):
    """What the page shows of a party's place: its score, band and bloc; the bloc only, 'none', without a score."""
    if left_right is None:
        return {'score': None, 'band': '', 'bloc': 'none', 'inferredFrom': ''}
    key, bloc = band(left_right.score)
    return {'score': round(left_right.score, 2), 'band': str(compass.POSITIONS[key]), 'bloc': bloc,
            'inferredFrom': left_right.inferred_from}


def blocs():
    """The blocs, for the page: key, name, which bands they join, colour."""
    return [{'key': key, 'name': str(bloc['name']), 'bands': str(bloc['bands']), 'color': bloc['color']}
            for key, bloc in BLOCS.items()]
