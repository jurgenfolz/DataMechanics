"""Builds data/politics/<country>/positions.csv: where expert surveys place a country's parties on two axes.

Brazil has three surveys, Germany and Austria two (CHES Europe 2024 and the Global Party Survey 2019).
Run it with `.venv/bin/python tools/party_positions.py`; it downloads the surveys and writes the files.
The site reads the file through the curated ETL (providers/curated/party_positions.py), not this script.

Both axes run from 0 to 10.
The economic axis runs from the left (the state plays an active role in the economy) to the right (a smaller role).
The social axis runs from progressive (expanded personal freedoms) to conservative (order, tradition, religion).
Each survey asked its own questions, so each is converted on its own and they are never averaged together.

CHES Latin America 2020 asked for both axes directly (LRECON and GALTAN, 0 to 10).
The Global Party Survey 2019 asked for both axes directly too (Q3.1 and Q3.3, 0 to 10).
Its party file leaves out two Brazilian parties its experts placed, PSD and PR, so the means come from the experts' answers.
PREPPS Latam 2018–2019 asked about single issues on a 1 to 20 scale.
Its economic axis is the mean of four economic issues: taxes and spending, privatization, deregulation, redistribution.
Its social axis is the mean of four social issues: social policy, religion, minorities, liberties and security.
Issues that run the other way are turned first, so 20 is always the right or the conservative end.
Both are then stretched from 1–20 to 0–10.
CHES Europe 2024 asked for both axes directly too (lrecon and galtan, 0 to 10); its expert file gives each answer.

In Brazil, some relevant parties are missing from a survey, so their places there are inferred, and marked as such.
A party that merged from others (União Brasil, from DEM and PSL) takes the average of the parties it came from.
Any other takes the place its left-right score predicts. That score comes from a 2018 survey of 519 Brazilian political
scientists, who placed every party on one 0 to 10 scale (Bolognesi, Ribeiro and Codato).
For each survey and axis, a straight line is fitted through the parties both surveys placed, and the missing party's
score is read off it. How well the line fits (its R²) is kept with the inferred place.
"""

import csv
import functools
import io
import statistics
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / 'data' / 'politics'
OUTPUT = DATA / 'brazil' / 'positions.csv'
USER_AGENT = 'DataMechanics/1.0 (https://data-mechanics.com)'

PREPPS = 'https://dataverse.harvard.edu/api/access/datafile/6435345'  # PREPPS Latam V3, doi:10.7910/DVN/TYVFC3
CHES = 'https://github.com/chesdata/chesdata.github.io/releases/download/ches-la/ches_la_2020_expert_level_v01.csv'
GPS = 'https://dataverse.harvard.edu/api/access/datafile/3679272'  # Global Party Survey by expert, doi:10.7910/DVN/WMGTNS
LEFT_RIGHT = 'https://dataverse.harvard.edu/api/access/datafile/6417803'  # Bolognesi, Ribeiro and Codato 2018, doi:10.7910/DVN/RDR3AK
CHES_EUROPE = 'https://github.com/chesdata/chesdata.github.io/releases/download/ches-europe/CHES_2024_ALL_Stacked_Expert.csv'

# Germany and Austria: the folder in data/politics/, then each survey's name for the country and its names for the
# parties -> our keys. The parties are those in the national parliament, and in Germany those that won at least
# 3 percent in 2025.
EUROPE = {
    'germany': {
        'ches': ('Germany', {'CDU': 'cdu', 'CSU': 'csu', 'SPD': 'spd', 'Grunen': 'gruene', 'FDP': 'fdp', 'AfD': 'afd',
                             'DL': 'linke', 'BSW': 'bsw'}),
        'gps': ('DEU', {'Christian Democratic Union': 'cdu', 'Christian Social Union in Bavaria': 'csu',
                        'Social Democratic Party': 'spd', 'Alliance 90/The Greens': 'gruene', 'Free Democratic Party': 'fdp',
                        'Alternative for Germany': 'afd', 'The Left': 'linke'}),
    },
    'austria': {
        'ches': ('Austria', {'OVP': 'ovp', 'SPO': 'spo', 'FPO': 'fpo', 'NEOS': 'neos', 'Grune': 'gruene'}),
        'gps': ('AUT', {"Austrian People's Party": 'ovp', 'Social Democratic Party of Austria': 'spo',
                        'Freedom Party of Austria': 'fpo', 'NEOS – The New Austria': 'neos',
                        'The Greens – The Green Alternative': 'gruene'}),
    },
}

# Each survey's name or code for a party -> (our key in party_profiles.csv, the name the party had then, if it differs).
PREPPS_PARTIES = {
    '301': ('pdt', ''), '302': ('dem', ''), '303': ('pl', 'PR'), '304': ('mdb', ''), '305': ('pp', ''),
    '306': ('psb', ''), '307': ('psdb', ''), '308': ('pt', ''), '309': ('ptb', ''), '310': ('republicanos', 'PRB'),
    '311': ('psd', ''), '312': ('podemos', ''), '313': ('novo', ''), '314': ('psol', ''), '315': ('pv', ''),
    '316': ('rede', ''), '317': ('psl', ''),
}
CHES_PARTIES = {
    'PT': ('pt', ''), 'PS': ('psb', ''), 'PDT': ('pdt', ''), 'PSDB': ('psdb', ''), 'MDB': ('mdb', ''),
    'PSD': ('psd', ''), 'DEM': ('dem', ''), 'PR': ('pl', 'PR'), 'PP': ('pp', ''), 'PRB': ('republicanos', 'PRB'),
    'PSL': ('psl', ''),
}
GPS_PARTIES = {
    "Workers' Party": ('pt', ''), 'Social Liberal Party': ('psl', ''), 'Progressive Party': ('pp', ''),
    'Party of the Brazilian Democratic Movement': ('mdb', ''), 'Social Democratic Party': ('psd', ''),
    'Republic Party': ('pl', 'PR'), 'Brazilian Socialist Party': ('psb', ''),
    'Brazilian Republican Party': ('republicanos', 'PRB'), 'Democrats': ('dem', ''),
    'Social Democracy Party': ('psdb', ''),
}

# The 2018 left-right survey's column for a party -> our key. Patriota is there only to infer PRD, which it helped found.
LEFT_RIGHT_PARTIES = {
    'MDB': 'mdb', 'PTB': 'ptb', 'PDT': 'pdt', 'PT': 'pt', 'DEM': 'dem', 'PCdoB': 'pcdob', 'PSB': 'psb', 'PSDB': 'psdb',
    'PPS': 'cidadania', 'PV': 'pv', 'Avante': 'avante', 'Progressistas': 'pp', 'PODE': 'podemos', 'PSL': 'psl',
    'PRB': 'republicanos', 'PSOL': 'psol', 'PR': 'pl', 'PSD': 'psd', 'PATRI': 'patriota', 'SDD': 'solidariedade',
    'NOVO': 'novo', 'REDE': 'rede',
}

# The parties every survey's compass shows, measured or inferred: those with at least two deputies or a senator in
# October 2026 (Câmara dos Deputados and Senado Federal open data).
RELEVANT = ['pt', 'psol', 'psb', 'pdt', 'pv', 'rede', 'pcdob', 'mdb', 'psdb', 'psd', 'podemos', 'pp', 'pl', 'republicanos',
            'uniao', 'novo', 'avante', 'solidariedade', 'prd', 'cidadania']

# A party formed by a merger -> the parties it came from, and how the page names them.
MERGERS = {'uniao': (('dem', 'psl'), 'DEM, PSL'), 'prd': (('ptb', 'patriota'), 'PTB, Patriota')}

# PREPPS issue numbers. True turns an issue round, so that its 20 is the right or the conservative end.
PREPPS_ECONOMIC = {1: False, 3: False, 4: False, 6: False}  # taxes v. spending, privatization, deregulation, redistribution
PREPPS_SOCIAL = {2: False, 10: True, 11: True, 12: False}  # social policy, religion, minorities, liberties v. security


@functools.cache
def download(url):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read().decode('utf-8', errors='replace')


def number(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def prepps():
    rows = csv.DictReader(io.StringIO(download(PREPPS)), delimiter='\t')
    issues = {}  # party code -> {issue: (score, answers)}
    for row in rows:
        if row['country'] != 'Brazil' or row['pres'].strip() or not row['dimensionid']:
            continue
        code = row['ptyid'].split('.')[0]
        score, answers = number(row['score_pos']), number(row['n_pos'])
        if code in PREPPS_PARTIES and score is not None:
            issues.setdefault(code, {})[int(float(row['dimensionid']))] = (score, int(answers or 0))
    for code, (key, then) in PREPPS_PARTIES.items():
        found = issues[code]
        axis = lambda wanted: statistics.mean(21 - found[i][0] if turned else found[i][0] for i, turned in wanted.items())
        # The fewest answers behind any of the eight issues: what the party's place rests on at least.
        answers = min(found[i][1] for i in {**PREPPS_ECONOMIC, **PREPPS_SOCIAL})
        yield 'prepps', key, then, stretch(axis(PREPPS_ECONOMIC)), stretch(axis(PREPPS_SOCIAL)), answers


def stretch(value):
    """A 1–20 PREPPS score on the 0–10 scale of the other surveys."""
    return (value - 1) / 19 * 10


def ches():
    rows = [row for row in csv.DictReader(io.StringIO(download(CHES))) if row['country_abb'] == 'BR']
    for code, (key, then) in CHES_PARTIES.items():
        economic = [x for x in (number(r['lrecon']) for r in rows if r['party_abb'] == code) if x is not None]
        social = [x for x in (number(r['galtan']) for r in rows if r['party_abb'] == code) if x is not None]
        yield 'ches', key, then, statistics.mean(economic), statistics.mean(social), min(len(economic), len(social))


def gps(iso='BRA', parties=GPS_PARTIES):
    """A country's places in the Global Party Survey; `parties` maps the survey's names to (key, name then)."""
    rows = [row for row in csv.DictReader(io.StringIO(download(GPS)), delimiter='\t') if row['ISO'] == iso]
    for slot in range(1, 11):
        name = rows[0][f'CPARTY{slot}'].removeprefix(f'{iso}_').strip('  Â')
        if name not in parties:
            continue  # a party no longer relevant, like Austria's Liste Pilz
        key, then = parties[name]
        answers = lambda question: [x for x in (number(r[f'{question}_{slot}']) for r in rows) if x is not None and 0 <= x <= 10]
        economic, social = answers('Q3.1'), answers('Q3.3')
        yield 'gps', key, then, statistics.mean(economic), statistics.mean(social), min(len(economic), len(social))


def left_right():
    """Each party's mean place on the 2018 survey's left-right scale, and how many experts placed it: {key: (score, n)}."""
    rows = list(csv.DictReader(io.StringIO(download(LEFT_RIGHT)), delimiter='\t'))
    scores = {}
    for code, key in LEFT_RIGHT_PARTIES.items():
        found = [x for x in (number(row[code]) for row in rows) if x is not None and 0 <= x <= 10]
        scores[key] = (statistics.mean(found), len(found))
    return scores


def fit(pairs):
    """The straight line through (x, y) pairs by least squares: (intercept, slope, R²)."""
    xs, ys = [x for x, _ in pairs], [y for _, y in pairs]
    slope, intercept = statistics.linear_regression(xs, ys)
    predicted = [intercept + slope * x for x in xs]
    mean = statistics.mean(ys)
    total = sum((y - mean) ** 2 for y in ys)
    rest = sum((y - p) ** 2 for y, p in zip(ys, predicted))
    return intercept, slope, 1 - rest / total


def inferred(survey, measured, scores):
    """The relevant parties a survey left out, with inferred places: rows like the measured ones, marked how."""
    placed = {key: (economic, social) for _, key, _, economic, social, _ in measured}
    common = [key for key in placed if key in scores]
    lines = [fit([(scores[key][0], placed[key][axis]) for key in common]) for axis in (0, 1)]
    clamp = lambda value: min(10, max(0, value))
    from_scale = lambda key: tuple(clamp(a + b * scores[key][0]) for a, b, _ in lines)
    place = lambda key: placed.get(key) or from_scale(key)
    for key in RELEVANT:
        if key in placed:
            continue
        if key in MERGERS:
            founders, names = MERGERS[key]
            economic, social = (statistics.mean(place(founder)[axis] for founder in founders) for axis in (0, 1))
            yield survey, key, '', economic, social, 0, 'merger', names, '', ''
        else:
            economic, social = from_scale(key)
            yield survey, key, '', economic, social, scores[key][1], 'scale', '', lines[0][2], lines[1][2]


def ches_europe(country, parties):
    """A country's places in CHES Europe 2024, from its experts' answers; `parties` maps CHES's names to our keys."""
    rows = [row for row in csv.DictReader(io.StringIO(download(CHES_EUROPE).lstrip('\ufeff'))) if row['cname'] == country]
    for name, key in parties.items():
        answers = lambda question: [x for x in (number(r[question]) for r in rows if r['party_name'] == name)
                                    if x is not None and 0 <= x <= 10]
        economic, social = answers('lrecon'), answers('galtan')
        yield 'ches-europe', key, '', statistics.mean(economic), statistics.mean(social), min(len(economic), len(social))


def write(path, rows):
    with open(path, 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file, lineterminator='\n')
        writer.writerow(['survey', 'party', 'name_at_survey', 'economic', 'social', 'experts', 'inferred', 'inferred_from',
                         'economic_fit', 'social_fit'])
        for survey, key, then, economic, social, experts, how, origin, economic_fit, social_fit in rows:
            fits = [f'{value:.2f}' if value != '' else '' for value in (economic_fit, social_fit)]
            writer.writerow([survey, key, then, f'{economic:.2f}', f'{social:.2f}', experts, how, origin, *fits])
    print(f'{path}: {len(rows)} rows')


def main():
    scores = left_right()
    rows = []
    for survey, measured in (('prepps', list(prepps())), ('ches', list(ches())), ('gps', list(gps()))):
        rows += [(*row, '', '', '', '') for row in measured]
        rows += list(inferred(survey, measured, scores))
    write(OUTPUT, rows)
    # Germany and Austria: every survey's own places, none inferred.
    for folder, surveys in EUROPE.items():
        iso, names = surveys['gps']
        measured = [*ches_europe(*surveys['ches']), *gps(iso, {name: (key, '') for name, key in names.items()})]
        write(DATA / folder / 'positions.csv', [(*row, '', '', '', '') for row in measured])


if __name__ == '__main__':
    main()
