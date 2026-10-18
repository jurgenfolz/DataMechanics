"""How values of each unit are written. The rules live in UNITS only.

static/js/lib/format.js applies the same rules in the browser: the page hands it UNITS as JSON.
"""

UNITS = {
    # compact: write 1.2 k / 3.4 m / 5.6 bn / 7.8 tn, with `digits` significant digits.
    'usd': {'prefix': '$', 'compact': True, 'digits': 3},
    'people': {'compact': True, 'digits': 3},
    # decimals: a fixed number of decimals.
    'percent': {'suffix': '%', 'decimals': 1},
    'years': {'suffix': ' yrs', 'decimals': 1},
    'per_1000': {'suffix': ' per 1,000', 'decimals': 1},
    'per_100k': {'suffix': ' per 100k', 'decimals': 1},
    'per_woman': {'suffix': ' per woman', 'decimals': 2},
    'tonnes': {'suffix': ' t', 'decimals': 1},
    'tonnes_total': {'compact': True, 'digits': 3, 'suffix': ' t'},
    'index': {'decimals': 3},
    'score': {'decimals': 2},
    'points': {'decimals': 1},
}

_SCALES = [(1e12, 'tn'), (1e9, 'bn'), (1e6, 'm'), (1e3, 'k')]


# Units longer than this ("per 1,000", "per woman") are left out where space is tight and the label names them.
SHORT_SUFFIX = 4


def format_value(value, unit, compact=False):
    """compact=True drops a long unit (see SHORT_SUFFIX); static/js/metric-page.js applies the same rule."""
    if value is None:
        return '–'
    rule = UNITS[unit]
    if compact and len(rule.get('suffix', '')) > SHORT_SUFFIX:
        rule = {**rule, 'suffix': ''}
    if rule.get('compact'):
        number = _compact(value, rule['digits'])
    else:
        number = f'{value:,.{rule["decimals"]}f}'
    return f'{rule.get("prefix", "")}{number}{rule.get("suffix", "")}'



def _compact(value, digits):
    for size, suffix in _SCALES:
        if abs(value) >= size:
            return f'{value / size:.{digits}g} {suffix}'
    return f'{value:.{digits}g}'
