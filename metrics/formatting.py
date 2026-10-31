"""How values of each unit are written, in every language. The rules live here only.

static/js/lib/format.js applies the same rules in the browser: the page hands it units() as JSON.
"""

from functools import cache

from django.utils import formats, translation
from django.utils.functional import Promise
from django.utils.translation import pgettext_lazy

# The rules, with their words in English. units() puts them into the active language.
UNITS = {
    # compact: write 1.2 k / 3.4 m / 5.6 bn / 7.8 tn, with `digits` significant digits.
    'usd': {'prefix': pgettext_lazy('unit', '$'), 'compact': True, 'digits': 3},
    'people': {'compact': True, 'digits': 3},
    'count': {'compact': True, 'digits': 3},  # things counted, like journal articles
    # decimals: a fixed number of decimals.
    'percent': {'suffix': '%', 'decimals': 1},
    # long: a unit left out where space is tight; the label next to the number names it.
    'years': {'suffix': pgettext_lazy('unit', ' yrs'), 'decimals': 1},
    'per_1000': {'suffix': pgettext_lazy('unit', ' per 1,000'), 'decimals': 1, 'long': True},
    'per_100k': {'suffix': pgettext_lazy('unit', ' per 100k'), 'decimals': 1, 'long': True},
    'per_woman': {'suffix': pgettext_lazy('unit', ' per woman'), 'decimals': 2, 'long': True},
    'tonnes': {'suffix': pgettext_lazy('unit', ' t'), 'decimals': 1},
    'ugm3': {'suffix': pgettext_lazy('unit', ' µg/m³'), 'decimals': 1},  # micrograms per cubic metre of air
    'tonnes_total': {'compact': True, 'digits': 3, 'suffix': pgettext_lazy('unit', ' t')},
    'index': {'decimals': 3},
    'score': {'decimals': 2},
    'points': {'decimals': 1},
    'score_100': {'decimals': 0},  # a whole-number score out of 100, like the Corruption Perceptions Index
    'litres': {'suffix': pgettext_lazy('unit', ' l'), 'decimals': 1},
    'kgoe': {'suffix': pgettext_lazy('unit', ' kgoe'), 'decimals': 0},  # kilograms of oil equivalent
    'kwh': {'suffix': pgettext_lazy('unit', ' kWh'), 'decimals': 0},
    'per_100': {'suffix': pgettext_lazy('unit', ' per 100'), 'decimals': 1, 'long': True},
    'months': {'suffix': pgettext_lazy('unit', ' months'), 'decimals': 1, 'long': True},
    'hours': {'suffix': pgettext_lazy('unit', ' h'), 'decimals': 0},
    'celsius': {'suffix': pgettext_lazy('unit', ' °C'), 'decimals': 2},
    'kcal': {'suffix': pgettext_lazy('unit', ' kcal'), 'decimals': 0},
    'twh': {'suffix': pgettext_lazy('unit', ' TWh'), 'decimals': 0},
    'kg_ha': {'suffix': pgettext_lazy('unit', ' kg/ha'), 'decimals': 0},
    'hectares': {'suffix': pgettext_lazy('unit', ' ha'), 'decimals': 2},
    'currency': {'compact': True, 'digits': 3},  # units of a local currency per US dollar
}

SCALES = [
    (1e12, pgettext_lazy('unit', 'tn')),
    (1e9, pgettext_lazy('unit', 'bn')),
    (1e6, pgettext_lazy('unit', 'm')),
    (1e3, pgettext_lazy('unit', 'k')),
]


def units():
    """The rules in the active language: its words for each unit and scale, and its decimal and thousands marks."""
    return _units(translation.get_language())


@cache
def _units(language):
    with translation.override(language):
        number = {
            'decimal': formats.get_format('DECIMAL_SEPARATOR'),
            'group': formats.get_format('THOUSAND_SEPARATOR'),
            'scales': [[size, str(name)] for size, name in SCALES],
        }
        return {
            unit: {**{key: str(value) if isinstance(value, Promise) else value for key, value in rule.items()}, **number}
            for unit, rule in UNITS.items()
        }


def format_value(value, unit, compact=False):
    """compact=True drops a long unit (see UNITS); static/js/metric-page.js applies the same rule."""
    if value is None:
        return '–'
    rule = units()[unit]
    suffix = rule.get('suffix', '')
    if compact and rule.get('long'):
        suffix = ''
    if rule.get('compact'):
        number = _compact(value, rule)
    else:
        number = _marks(f'{value:,.{rule["decimals"]}f}', rule)
    return f'{rule.get("prefix", "")}{number}{suffix}'


def change_amount(start, end, relative=False):
    """The change from start to end, with its sign: in percent of the start when relative (and the start is above 0), else in the unit."""
    if relative and start > 0:
        return (end - start) / start * 100
    return end - start


def format_change(start, end, unit, relative=False):
    """How far a value moved from start to end, without the sign.

    relative=True writes the change in percent of the start value, for quantities that grow by multiplying, like GDP.
    Otherwise a change in a percentage is the difference of the two percentages (6.5% to 8% is 1.5%).
    Any other change is in the unit.
    """
    relative = relative and start > 0
    return format_amount(change_amount(start, end, relative), unit, relative)


def format_amount(amount, unit, relative=False):
    """The size of a change, without its sign: in percent when relative, otherwise as format_change says.

    formatAmount in static/js/lib/format.js writes changes the same way, for the reel's live count: change both together.
    """
    rule = units()[unit]
    size = abs(amount)
    if relative:
        return _marks(f'{size:.1f}' if size < 10 else f'{size:,.0f}', rule) + '%'
    if unit == 'percent':
        return f"{_marks(f'{size:,.1f}', rule)}%"
    return format_value(size, unit, compact=True)


def _compact(value, rule):
    for size, suffix in rule['scales']:
        if abs(value) >= size:
            return f"{_marks(f'{value / size:.{rule["digits"]}g}', rule)} {suffix}"
    return _marks(f'{value:.{rule["digits"]}g}', rule)


def _marks(number, rule):
    """Python writes 1,234.5; this swaps in the language's own thousands and decimal marks."""
    return number.translate({ord(','): rule['group'], ord('.'): rule['decimal']})
