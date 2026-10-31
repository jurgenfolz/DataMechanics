"""Builds the United States' crime per year for Politics mode, for the whole country and by state.
It writes data/politics/united-states/crime.csv: the columns year, state (empty for the whole country), crime, measure
and value.

Source: the FBI's estimated crimes, 1979 to the last year, from its Crime Data Explorer (public domain, as a work of
the federal government). One file gives the nation, the 50 states and the District of Columbia, with the population
the FBI divides by, for nine kinds of crime: the estimates fill in for the police agencies that did not report.
The file is fetched through the explorer's signed-address route, as its own download page does.
Rape has two series: the legacy definition to 2016, and the definition of 2013 from 2013.
The nation's rows for 2017 to 2020 are missing from the file, so those years are the sum of the states, as the other
years' nation rows are within 0.1% of their states' sums.

Usage: .venv/bin/python tools/united_states_crime.py
"""

import csv
import json
import re
import sys
import tempfile
import urllib.request
from datetime import date
from pathlib import Path

import spreadsheet  # tools/spreadsheet.py and tools/download.py, next to this file
from download import download

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'politics' / 'united-states' / 'crime.csv'
HEADERS = {'User-Agent': 'DataMechanics/1.0 (https://data-mechanics.com)'}
LAST = date.today().year - 1  # the last whole year

CDE = 'https://cde.ucr.cjis.gov/LATEST/'
MANIFEST = CDE + 'webapp/assets/JSON/downloads/downloads.json'  # names the file of the year
SIGNED = CDE + 's3/signedurl?key={key}'  # gives a signed address, good for 15 minutes

# The file's columns -> our keys. The counts are estimates of offences known to the police.
CRIMES = {
    'violent_crime': 'violent',
    'homicide': 'homicides',
    'rape_revised': 'rape',
    'rape_legacy': 'rape-legacy',
    'robbery': 'robbery',
    'aggravated_assault': 'aggravated-assault',
    'property_crime': 'property',
    'burglary': 'burglary',
    'larceny': 'larceny',
    'motor_vehicle_theft': 'vehicle-theft',
}
STATES = 51  # the 50 states and the District of Columbia


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=120) as response:
        return response.read()


def estimates_file(folder):
    """Downloads the estimated crimes file (an xlsx workbook, whatever its name says) and returns its path."""
    manifest = json.loads(get(MANIFEST))
    entry = next(item for item in manifest if item.get('id') == 'srs')
    key = entry['awsFile']
    signed = json.loads(get(SIGNED.format(key=key)))
    if key not in signed:
        sys.exit(f'No signed address for {key}')
    return download(signed[key], folder / 'estimates.xlsx')


def clean_name(name):
    """A state's name without the footnote digits and spaces the file adds ('     Florida3')."""
    return re.sub(r'\d+$', '', str(name or '')).strip()


def number(value):
    return None if value in (None, '', 'None') else float(value)


def read(path):
    """[(year, code or '' for the nation, {column: value})] from the file, with the state codes mended."""
    rows = spreadsheet.rows(path)
    header = rows[0]
    columns = {name: i for i, name in enumerate(header)}
    by_name = {}  # a state's name -> its code, to mend rows whose code is wrong
    found = []
    for row in rows[1:]:
        if not row or row[columns['year']] is None:
            continue
        values = {name: (row[i] if i < len(row) else None) for name, i in columns.items()}
        name = clean_name(values['state_name'])
        code = str(values['state_abbr'] or '').strip()
        if name and name != 'United States Total':
            by_name.setdefault(name, code)
            if by_name[name] != code:  # 2022 codes North Dakota as NC
                code = by_name[name]
            found.append((int(values['year']), f'US-{code}', values))
        else:
            found.append((int(values['year']), '', values))
    return found


def main():
    with tempfile.TemporaryDirectory() as temporary:
        found = read(estimates_file(Path(temporary)))
    years = sorted({year for year, _, _ in found if year <= LAST})
    rows = []
    for year in years:
        states = [(code, values) for found_year, code, values in found if found_year == year and code]
        if len(states) != STATES:
            sys.exit(f'{year}: {len(states)} states instead of {STATES}')
        nation = next((values for found_year, code, values in found if found_year == year and not code), None)
        if nation is None:
            nation = {column: sum(number(values[column]) or 0 for _, values in states) for column in ['population', *CRIMES]}
            for column in CRIMES:  # a column every state leaves empty (rape_revised before 2013) stays empty
                if all(number(values[column]) is None for _, values in states):
                    nation[column] = None
        for code, values in [('', nation), *states]:
            people = number(values['population'])
            for column, key in CRIMES.items():
                count = number(values[column])
                if count is None:
                    continue
                rows.append((year, code, key, 'count', count))
                if people:
                    rows.append((year, code, key, 'rate', round(count / people * 100000, 4)))
    rows.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    with open(OUT, 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['year', 'state', 'crime', 'measure', 'value'])
        writer.writerows(rows)
    print(f'{len(rows)} rows -> {OUT}')


if __name__ == '__main__':
    main()
