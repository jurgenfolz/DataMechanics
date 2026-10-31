"""Builds data/politics/<country>/left_right.csv: where political scientists place a country's parties on one left-right scale.

Run it with `.venv/bin/python tools/party_left_right.py`; it downloads the surveys and writes the files.
The site reads the file through the curated ETL (providers/curated/party_left_right.py), not this script.

The survey asked Brazilian political scientists to place every party from 0, the far left, to 10, the far right.
It ran in 2018 and 2022 (Bolognesi, Codato, Ribeiro and Silva, Harvard Dataverse, CC0); this file takes 2022.
A party's score is the mean of the experts who placed it.
PRD was formed after the survey, by PTB and Patriota, so it takes the average of their two scores, marked as such.
The European countries' scores come from the general left-right question (lrgen, 0 to 10) of CHES Europe 2024, the
mean of the experts who answered it. Italy's AVS, the joint list of Europa Verde and Sinistra Italiana, takes the
average of the two, marked as such.
The United States' scores come from the 2019 Global Party Survey, which asked no general left-right question: they are
its economic one (Q3.1, 0 to 10), and the page says so.
politics/spectrum.py turns a score into left, centre or right.
"""

import csv
import io
import statistics

from party_positions import CHES_EUROPE, DATA, EUROPE, GPS, download, number, two

OUTPUT = DATA / 'brazil' / 'left_right.csv'
SURVEY = 'https://dataverse.harvard.edu/api/access/datafile/10898288'  # df_experts.csv, doi:10.7910/DVN/MFIXKW
WAVE = '22'

# The survey's column for a party in the 2022 wave -> our key in party_profiles.csv.
# Patriota is there only to infer PRD, which it helped found.
PARTIES = {
    'mdb': 'mdb', 'uniao': 'uniao', 'ptb': 'ptb', 'pdt': 'pdt', 'pt': 'pt', 'p_cdo_b': 'pcdob', 'psb': 'psb', 'psdb': 'psdb',
    'cdd': 'cidadania', 'pv': 'pv', 'avante': 'avante', 'progre': 'pp', 'dc': 'dc', 'podemos': 'podemos',
    'rep': 'republicanos', 'psol': 'psol', 'pl': 'pl', 'psd': 'psd', 'patri': 'patriota', 'sdd': 'solidariedade',
    'novo': 'novo', 'rede': 'rede',
}

# A party formed after the survey by a merger -> the parties it came from, and how the page names them.
MERGERS = {'prd': (('ptb', 'patriota'), 'PTB, Patriota')}

# Joint lists in the European countries: folder -> {our key: (the parties it joins, how the page names them)}.
JOINT = {'italy': {'avs': (('ev', 'si'), 'EV, SI')}}

# The United States in the Global Party Survey: its names for the parties -> our keys.
USA = {'Republican Party': 'republican', 'Democratic Party': 'democratic'}


def scores():
    """Each party's mean score in the wave, and how many experts placed it: {key: (score, experts)}."""
    rows = list(csv.DictReader(io.StringIO(download(SURVEY).lstrip('﻿')), delimiter=';'))
    found = {}
    for column, key in PARTIES.items():
        values = [x for x in (number(row[f'ideol_{WAVE}_{column}'].replace(',', '.')) for row in rows) if x is not None and 0 <= x <= 10]
        found[key] = (statistics.mean(values), len(values))
    return found


def ches_europe(country, parties):
    """A country's general left-right places in CHES Europe 2024, from its experts' answers: (key, score, experts, '')."""
    rows = [row for row in csv.DictReader(io.StringIO(download(CHES_EUROPE).lstrip('\ufeff'))) if row['cname'] == country]
    for name, key in parties.items():
        key = key[0] if isinstance(key, tuple) else key  # (key, the party's name then)
        values = [x for x in (number(r['lrgen']) for r in rows if r['party_name'] == name) if x is not None and 0 <= x <= 10]
        yield key, statistics.mean(values), len(values), ''


def gps_economic(iso, parties):
    """A country's economic left-right places in the Global Party Survey 2019 (Q3.1): (key, score, experts, '')."""
    rows = [row for row in csv.DictReader(io.StringIO(download(GPS)), delimiter='\t') if row['ISO'] == iso]
    for slot in range(1, 11):
        name = rows[0][f'CPARTY{slot}'].removeprefix(f'{iso}_').strip('\xa0 Â')
        if name in parties:
            values = [x for x in (number(r[f'Q3.1_{slot}']) for r in rows) if x is not None and 0 <= x <= 10]
            yield parties[name], statistics.mean(values), len(values), ''


def write(path, rows):
    with open(path, 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file, lineterminator='\n')
        writer.writerow(['party', 'score', 'experts', 'inferred_from'])
        for key, score, experts, origin in sorted(rows, key=lambda row: row[1]):
            writer.writerow([key, two(score), experts, origin])
    print(f'{path}: {len(rows)} rows')


def main():
    found = scores()
    rows = [(key, score, experts, '') for key, (score, experts) in found.items() if key != 'patriota']
    for key, (founders, names) in MERGERS.items():
        rows.append((key, statistics.mean(found[f][0] for f in founders), min(found[f][1] for f in founders), names))
    write(OUTPUT, rows)
    for folder, surveys in EUROPE.items():
        rows = list(ches_europe(*surveys['ches']))
        found = {key: (score, experts) for key, score, experts, _ in rows}
        for key, (parts, names) in JOINT.get(folder, {}).items():
            rows.append((key, statistics.mean(found[p][0] for p in parts), min(found[p][1] for p in parts), names))
        write(DATA / folder / 'left_right.csv', rows)
    write(DATA / 'united-states' / 'left_right.csv', list(gps_economic('USA', USA)))


if __name__ == '__main__':
    main()
