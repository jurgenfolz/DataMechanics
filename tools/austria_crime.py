"""Builds Austria's crime per year for Politics mode, for the whole country and by Bundesland.
It writes data/politics/austria/crime.csv: the columns year, state (empty for the whole country), crime, measure and value.

Sources:
- Police crime statistics (Polizeiliche Kriminalstatistik, PKS) by offence, from the Interior Ministry's yearly
  "Kriminalitätsbericht – Statistik und Analyse" (REPORTS): reported cases, attempts, cleared cases and the clearance
  rate, for the whole country (Teil B, Grundtabelle) and each Bundesland (Teil C, Tabelle 1), 2010 to 2023.
  The tool reads the PDFs with pdftotext, which keeps the columns.
  The 2022 and 2023 editions come from the Parliament's copies: bmi.gv.at's 2022 file is cut short.
- The Bundeskriminalamt's PKS brochures for 2024 and 2025 (BROCHURES). Their ten-year tables give the whole country's
  total, robbery, rape and drug offences, the PKS's own groups (violent crime, property crime, burglary in homes,
  vehicle theft, cybercrime, internet fraud) and each Bundesland's total.
  They fill the years the Kriminalitätsbericht does not cover yet; where both give a year, the Kriminalitätsbericht
  wins and the tool prints any disagreement.
  bundeskriminalamt.at's Impressum allows reuse for non-commercial ends with the source named.
- Convictions since 1947: Statistik Austria's Verurteilungsstatistik (CONVICTIONS, CC BY 4.0), its table V3.
- Population: Statistik Austria's population on 1 January by Bundesland, from 1952 (POPULATION, CC BY 4.0).
  The file is the population projection. Its observed years are the ones where every scenario gives the same value.
  A year's rate divides by the average of its 1 January and the next, our mid-year estimate, from observed years only.

Usage: .venv/bin/python tools/austria_crime.py
"""

import csv
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import ods  # tools/ods.py and tools/download.py, next to this file
from download import download

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'politics' / 'austria' / 'crime.csv'
LAST = date.today().year - 1  # the last whole year

BMI = 'https://www.bmi.gv.at/508/files/'
PARLIAMENT = 'https://www.parlament.gv.at/dokument/'
REPORTS = {
    2010: BMI + 'sicherheitsbericht_2010_kriminalittsbericht_statistik.pdf',
    2011: BMI + 'kriminalitaetsbericht_2011a.pdf',
    2012: BMI + '2_kriminalitaetsbericht_2012.pdf',
    2013: BMI + '03_kriminalitaetsbericht_2013_statistik.pdf',
    2014: BMI + 'kriminalitaetsbericht_2014_bk.pdf',
    2015: BMI + 'kriminalitaetsbericht_statistik_2015.pdf',
    2016: BMI + 'sib_2016/03_sib2016-kriminalitaetsbericht_web.pdf',
    2017: BMI + 'sib_2017/03_sib_2017-kriminalitasetsbericht_web.pdf',
    2018: BMI + 'sib_2018/3_sib_2018_kriminalitaetsbericht_web.pdf',
    2019: BMI + 'sib_2019/3_sib_2019_kriminalitaetsbericht_2019_statistik_und_analyse.pdf',
    2020: BMI + 'sib_2020/sib2020-kriminalitaetsbericht-2020.pdf',
    2021: BMI + 'sib_2021/kriminalitaetsbericht_-_statistik_und_analyse.pdf',
    2022: PARLIAMENT + 'XXVII/III/1150/imfname_1622875.pdf',
    2023: PARLIAMENT + 'XXVIII/III/184/imfname_1693671.pdf',
}
BK = 'https://www.bundeskriminalamt.at/501/files/'
BROCHURES = {2024: BK + 'PKS-24-web3_bf_20250919.pdf', 2025: BK + 'kriminalpolizeiliche_anzeigenstatistik_2025_bf.pdf'}
CONVICTIONS = 'https://www.statistik.at/fileadmin/pages/356/3_VERURTEILUNGEN_2025.ods'
POPULATION = 'https://data.statistik.gv.at/data/OGD_bevjahresanf_PR_BEVJA_11.csv'

# The Grundtabelle's regions, as its page header names them -> ISO 3166-2 ('' for the whole country).
STATES = {'ÖSTERREICH': '', 'BURGENLAND': 'AT-1', 'KÄRNTEN': 'AT-2', 'NIEDERÖSTERREICH': 'AT-3',
          'OBERÖSTERREICH': 'AT-4', 'SALZBURG': 'AT-5', 'STEIERMARK': 'AT-6', 'TIROL': 'AT-7', 'VORARLBERG': 'AT-8',
          'WIEN': 'AT-9'}
NAMES = {'AT-1': 'Burgenland', 'AT-2': 'Kärnten', 'AT-3': 'Niederösterreich', 'AT-4': 'Oberösterreich',
         'AT-5': 'Salzburg', 'AT-6': 'Steiermark', 'AT-7': 'Tirol', 'AT-8': 'Vorarlberg', 'AT-9': 'Wien'}

# Our key -> the Grundtabelle's codes (its KENNZAHL column) that add up to it.
# A code with /V is the offence's Verbrechen row where the table splits it from the Vergehen row.
# The 2016 reform of the StGB split § 84 and § 129 into two rows each; the sums stay comparable.
# SMG, the drug law, is in the Grundtabelle to 2013 only. 590 is the total of every offence, StGB and other laws.
CRIMES = {
    'total': ('590',),
    'murder': ('75',),
    'assault': ('83',),
    'serious-assault': ('84', '84/V'),
    'coercion': ('105',),
    'threat': ('107',),
    'criminal-damage': ('125', '126', '126/V'),
    'theft': ('127',),
    'burglary': ('129', '129/V'),
    'robbery': ('142', '143'),
    'fraud': ('146', '147', '147/V'),
    'computer-fraud': ('148a', '148a/V'),
    'rape': ('201',),
    'drugs': ('SMG',),
}

# The brochures' ten-year tables: our key -> the caption that names the table, the columns (from 0) whose values add
# up to the cases, and the column of the clearance rate, or None.
# The 2025 brochure prints a caption under its table ("Tabelle 6"), the 2024 one above ("Tabelle: Entwicklung ...").
TABLES = {
    2025: {
        'total': (r'Entwicklung der Gesamtkriminalität in Österreich', (0,), 2),
        'violent-crime': (r'Entwicklung der Gewaltkriminalität in Österreich', (0,), 2),
        'robbery': (r'Entwicklung der Raubdelikte in Österreich', (0,), 2),
        'rape': (r'Entwicklung von Vergewaltigungen in Österreich', (0,), 2),
        'property-crime': (r'Sachverhaltes Eigentumskriminalität', (0,), 2),
        'home-burglary': (r'Entwicklung des Einbruchsdiebstahls in Wohnraum', (2,), None),  # attempts, completed, all
        'vehicle-theft': (r'Entwicklung des Diebstahles von Kraftfahrzeugen', (0,), 1),
        'cybercrime': (r'Sachverhaltes Cybercrime im engeren Sinn', (0,), 2),
        'internet-fraud': (r'Sachverhaltes Internetbetrug', (0,), 2),
        'drugs': (r'Entwicklung der Suchtmittelkriminalität in Österreich', (0,), 2),
        **{f'total {code}': (rf'Entwicklung der Gesamtkriminalität {name}\b', (0,), 2) for code, name in NAMES.items()},
    },
    2024: {
        'fraud': (r'Entwicklung der Betrugsdelikte von', (0, 1), None),  # § 146, § 147, § 148
    },
}

HEADER = re.compile(r'^\s*(?P<state>' + '|'.join(STATES) + r')\s+GRUNDTABELLE\s+TABELLE')
PART = re.compile(r'BLATT\s*\d+,\s*TEIL\s*1\b')  # part 1 of a sheet counts cases, part 2 suspects
COUNT = r'\d{1,3}(?:[. ]\d{3})*|-'  # '52.822', '2 198' (a thousands separator pdftotext turns into a space) or '-'
ROW = re.compile(rf'^\s*(?P<label>\S.*?)\s{{2,}}(?P<code>\S+)\s+(?P<cases>{COUNT})\s+(?P<attempts>{COUNT})\s+'
                 rf'(?P<frequency>[\d.,]+|-+)\s+(?P<cleared>{COUNT})\s+(?P<rate>[\d.,]+%|-+)\s*$')
YEAR_ROW = re.compile(r'^\s*(?:Jahr\s+)?(?P<year>20\d\d)\s{2,}(?P<columns>\S.*?)\s*$')
NEAR = 20  # a brochure table's rows lie within this many lines of its caption
YEARS = 5  # a brochure table has at least this many years; a shorter run of rows is something else


def count(text):
    """A count as the PDFs write it: '52.822', '537. 792', '35 915' or '-' (none)."""
    return int(re.sub(r'[.\s]', '', text)) if text != '-' else 0


def number(text):
    """A number as the brochures write it: '52,9 %', '1.248' or '- 7,4 %'."""
    cleaned = re.sub(r'[.\s%]', '', text).replace(',', '.')
    return float(cleaned) if cleaned and set(cleaned) != {'-'} else None


def pages(pdf, folder):
    """A PDF's pages as pdftotext lays them out, each a list of lines."""
    text = folder / (pdf.stem + '.txt')
    # Some editions make pdftotext print syntax warnings; the text still comes out whole.
    subprocess.run(['pdftotext', '-layout', str(pdf), str(text)], check=True, stderr=subprocess.DEVNULL)
    return [page.splitlines() for page in text.read_text(encoding='utf-8').split('\f')]


def report(year, folder):
    """{state: {code: (cases, attempts, cleared, clearance rate)}} from one Kriminalitätsbericht's Grundtabellen."""
    found = {}
    for page in pages(download(REPORTS[year], folder / f'kb{year}.pdf'), folder):
        head = page[:20]
        header = next((HEADER.match(line) for line in head if HEADER.match(line)), None)
        if header is None or not any(PART.search(line) for line in head):
            continue
        rows = found.setdefault(STATES[header['state']], {})
        for line in page:
            row = ROW.match(line)
            if row and row['code'] not in rows:
                rows[row['code']] = (count(row['cases']), count(row['attempts']), count(row['cleared']),
                                     number(row['rate']))
    missing = set(STATES.values()) - set(found)
    if missing:
        sys.exit(f'{year}: no Grundtabelle for {sorted(missing)}')
    return found


def tables(year, folder):
    """{key: {year: (cases, clearance rate or None)}} from one brochure's ten-year tables (TABLES)."""
    lines = [line for page in pages(download(BROCHURES[year], folder / f'pks{year}.pdf'), folder) for line in page]
    runs = []  # (first line, last line, {year: columns}) for each run of rows whose years go up
    for index, line in enumerate(lines):
        row = YEAR_ROW.match(line)
        if not row:
            continue
        columns = [number(column) for column in re.split(r'\s{2,}', row['columns'])]
        if any(column is None for column in columns):
            continue
        found = int(row['year'])
        if runs and found > max(runs[-1][2]) and index - runs[-1][1] <= NEAR:
            runs[-1][1] = index
            runs[-1][2][found] = columns
        else:
            runs.append([index, index, {found: columns}])
    result = {}
    for key, (caption, cases, rate) in TABLES[year].items():
        for index, line in enumerate(lines):
            if not re.search(caption, line):
                continue
            near = [run for run in runs if len(run[2]) >= YEARS and run[0] - NEAR <= index <= run[1] + NEAR]
            if near:
                run = min(near, key=lambda run: min(abs(run[0] - index), abs(run[1] - index)))
                result[key] = {found: (sum(columns[i] for i in cases), columns[rate] if rate is not None else None)
                               for found, columns in run[2].items()}
                break
        else:
            sys.exit(f'PKS {year}: no table for {key} ({caption})')
    return result


def convictions(folder):
    """{year: (all, violent, property, sexual)} convictions since 1947, from table V3."""
    result = {}
    for row in ods.rows(download(CONVICTIONS, folder / 'convictions.ods'), sheet='V3'):
        if row and str(row[0]).isdigit() and len(row) >= 7:
            result[int(row[0])] = tuple(float(row[column]) for column in (1, 2, 4, 6))
    if not result:
        sys.exit('No rows in table V3 of the convictions')
    return result


def population(folder):
    """{'' or an ISO 3166-2 code: {year: people on 1 January}} for the observed years, from Statistik Austria."""
    people = {}
    projected = set()
    with open(download(POPULATION, folder / 'population.csv'), encoding='utf-8', newline='') as file:
        for row in csv.reader(file, delimiter=';'):
            if row[0].startswith('C-'):
                continue
            state, year, scenarios = 'AT-' + row[0][-1], int(row[1][4:]), [int(value) for value in row[4:]]
            if len(set(scenarios)) > 1:
                projected.add(year)
            for code in (state, ''):
                people.setdefault(code, {})[year] = people.get(code, {}).get(year, 0) + scenarios[0]
    observed = {code: {year: value for year, value in years.items() if year not in projected}
                for code, years in people.items()}
    print(f'Population observed to 1 January {max(observed[""])}, projected from {min(projected)}')
    return observed


def mid_year(people, year):
    """The average of the people on 1 January of `year` and of the next, or None."""
    if year in people and year + 1 in people:
        return (people[year] + people[year + 1]) / 2
    return None


def main():
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        people = population(folder)
        sentenced = convictions(folder)
        reports = {year: report(year, folder) for year in REPORTS}
        brochures = {year: tables(year, folder) for year in BROCHURES}
    rows = []
    values = {}  # (year, state, key) -> cases, to fill from the brochures only where the reports have none

    def add(year, state, key, cases, clearance=None):
        values[year, state, key] = cases
        rows.append((year, state, key, 'cases', cases))
        rate = mid_year(people[state], year)
        if rate:
            rows.append((year, state, key, 'rate', round(cases / rate * 100000, 2)))
        if clearance is not None and cases:
            rows.append((year, state, key, 'clearance', round(clearance, 1)))

    absent = {}
    for year, states in sorted(reports.items()):
        for state, found in states.items():
            for key, codes in CRIMES.items():
                present = [found[code] for code in codes if code in found]
                if not present:
                    absent.setdefault((year, key), []).append(state)
                    continue
                cases = sum(row[0] for row in present)
                if len(codes) == 1:
                    clearance = present[0][3]  # the table's own rate
                else:
                    clearance = sum(row[2] for row in present) / cases * 100 if cases else None
                add(year, state, key, cases, clearance)
            if '75' in found:  # murders in which the victim died: the cases minus the attempts
                rows.append((year, state, 'murder', 'completed', found['75'][0] - found['75'][1]))
        totals = {state: values.get((year, state, 'total')) for state in STATES.values()}
        if sum(total for state, total in totals.items() if state) != totals['']:
            print(f'{year}: the states\' totals do not add up to the country\'s')
    for year, key_years in sorted(brochures.items()):
        for key, years in key_years.items():
            key, _, state = key.partition(' ')
            for found, (cases, clearance) in sorted(years.items()):
                if (found, state, key) in values:
                    if values[found, state, key] != cases:
                        print(f'PKS {year} gives {key} {state or "AT"} {found} as {cases:.0f}, '
                              f'the Kriminalitätsbericht as {values[found, state, key]:.0f}')
                elif found <= LAST:
                    add(found, state, key, int(cases), clearance)
    for year, (total, violent, property_, sexual) in sorted(sentenced.items()):
        if year > LAST:
            continue
        for key, value in (('convictions', total), ('convictions-violent', violent),
                           ('convictions-property', property_), ('convictions-sexual', sexual)):
            rows.append((year, '', key, 'convictions', int(value)))
            rate = mid_year(people[''], year)
            if rate:
                rows.append((year, '', key, 'convictions_rate', round(value / rate * 100000, 2)))
    for (year, key), states in sorted(absent.items()):
        print(f'{year}: no {key} rows for {len(states)} regions')
    rows.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    with open(OUT, 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['year', 'state', 'crime', 'measure', 'value'])
        writer.writerows(rows)
    print(f'{len(rows)} rows -> {OUT}')


if __name__ == '__main__':
    main()
