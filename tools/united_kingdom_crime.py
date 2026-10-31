"""Builds the United Kingdom's crime per year for Politics mode: England and Wales, for the whole country.
It writes data/politics/united-kingdom/crime.csv: the columns year, state (always empty), crime, measure and value.

The United Kingdom has no single crime series: Scotland and Northern Ireland count crime under their own rules.
So every figure here is for England and Wales.
There are no figures by area: the map's units do not match police areas.
Years run April to March, as the Home Office counts them: "Apr 2024 to Mar 2025" is written as 2024, the year most of its months are in.
The Homicide Index counts calendar years to 1996 and April-to-March years from 1997.

Sources, all under the Open Government Licence v3.0:
- Police recorded crime by offence, from the year ending March 2003: Table A5a of the ONS's "Crime in England and Wales: Appendix tables" (Home Office data).
  The newest edition is found through the dataset page's JSON (APPENDIX).
  Only the year-ending-March columns are read; the year-ending-June ones are skipped.
- Offences involving a knife or sharp instrument, from the year ending March 2020: Table 21 of the ONS's "Offences involving the use of weapons: data tables" (WEAPONS), the whole of England and Wales.
- Homicide, from 1960: Table 1 of the ONS's "Appendix tables: homicide in England and Wales", from the Home Office's Homicide Index (HOMICIDE).
  Offences currently recorded as homicide, which the index gives from 1967.
- Prisoners, from 2015: the Ministry of Justice's annual average prison population, the "Annual prison population" file of its Offender management statistics quarterly, found through gov.uk's content API (OMSQ).
- Population: the ONS's mid-year estimates of England and Wales, Table 7 of its estimates from 1838 (POPULATION).
  A year's rate divides by the mid-year estimate of its first calendar year.

Left out: the Home Office's recorded crime 1898 to 2001/02 and the prison population 1900 to 2013.
They are legacy .xls files, which Python's standard library cannot read.

Usage: .venv/bin/python tools/united_kingdom_crime.py
"""

import csv
import json
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import ods  # tools/ods.py and tools/spreadsheet.py, next to this file
import spreadsheet

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'politics' / 'united-kingdom' / 'crime.csv'
HEADERS = {'User-Agent': 'DataMechanics/1.0 (https://data-mechanics.com)'}
LAST = date.today().year - 1  # the last whole year
ATTEMPTS = 5  # the ONS answers 429 to a burst of downloads; a pause and another try get through

ONS = 'https://www.ons.gov.uk'
APPENDIX = '/peoplepopulationandcommunity/crimeandjustice/datasets/crimeinenglandandwalesappendixtables'
WEAPONS = '/peoplepopulationandcommunity/crimeandjustice/datasets/offencesinvolvingtheuseofweaponsdatatables'
HOMICIDE = '/peoplepopulationandcommunity/crimeandjustice/datasets/appendixtableshomicideinenglandandwales'
POPULATION = ('/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/'
              'populationestimatesforukenglandandwalesscotlandandnorthernireland')
POPULATION_EDITION = 'ukpopulationestimates1838to'  # the edition's address starts so; the end year changes
GOVUK = 'https://www.gov.uk/api/content'
OMSQ = '/government/collections/offender-management-statistics-quarterly'
ANNUAL_PRISON = 'Annual prison population'  # the attachment's title in the July edition

# Our key -> the offence group's row in Table A5a, by its label without the notes.
GROUPS = {
    'all': ('TOTAL RECORDED CRIME - ALL OFFENCES EXCLUDING FRAUD AND COMPUTER MISUSE',),
    'violence': ('TOTAL VIOLENCE AGAINST THE PERSON',),
    'violence-with-injury': ('Violence with injury',),
    'sexual-offences': ('TOTAL SEXUAL OFFENCES',),
    'rape': ('Rape',),
    'robbery': ('TOTAL ROBBERY',),
    'theft': ('TOTAL THEFT OFFENCES',),
    'burglary': ('Burglary',),
    'vehicle-offences': ('Vehicle offences',),
    'theft-from-person': ('Theft from the person',),
    'bicycle-theft': ('Bicycle theft',),
    'shoplifting': ('Shoplifting',),
    'criminal-damage': ('TOTAL CRIMINAL DAMAGE AND ARSON',),
    'drugs': ('TOTAL DRUG OFFENCES',),
    'weapons': ('TOTAL POSSESSION OF WEAPONS OFFENCES',),
    'public-order': ('TOTAL PUBLIC ORDER OFFENCES',),
}
KNIFE = 'Total selected offences'  # Table 21's total, homicide included
FISCAL = re.compile(r'Apr (\d{4}) to Mar \d{4}')
CALENDAR = re.compile(r'Jan (\d{4}) to Dec \d{4}')


def get(url):
    for attempt in range(ATTEMPTS):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=120) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == ATTEMPTS - 1:
                raise
            time.sleep(int(error.headers.get('Retry-After') or 10))


def fetch(url, path):
    """Saves `url` to `path` and returns the path."""
    path.write_bytes(get(url))
    return path


def local_date(timestamp):
    """An ONS or gov.uk timestamp as the day it names in London: '2026-10-21T23:00:00.000Z' is 2026-10-22."""
    return datetime.fromisoformat(timestamp.replace('Z', '+00:00')).astimezone(ZoneInfo('Europe/London')).date()


def ons_file(dataset, edition=None):
    """The address of an ONS dataset's newest file, through its page's JSON.
    The edition is the first one, or the one whose address ends with `edition`; the file is that edition's download.
    Prints the release date, to cite.
    """
    page = json.loads(get(f'{ONS}{dataset}/data'))
    uri = next(found['uri'] for found in page['datasets'] if edition is None or edition in found['uri'].rsplit('/', 1)[1])
    file = json.loads(get(f'{ONS}{uri}/data'))['downloads'][0]['file']
    print(f"{page['description']['title']}: released {local_date(page['description']['releaseDate'])}, {file}")
    return f'{ONS}/file?uri={uri}/{file}'


def prison_file():
    """The address of the newest "Annual prison population" file, from gov.uk's content API.
    The Offender management statistics quarterly collection lists its editions newest first, and the July edition carries the file.
    """
    for document in json.loads(get(GOVUK + OMSQ))['links']['documents']:
        edition = json.loads(get(GOVUK + document['base_path']))
        for attachment in edition['details']['attachments']:
            if attachment['title'].startswith(ANNUAL_PRISON):
                print(f"{document['title']}: released {local_date(edition['first_published_at'])}, {attachment['title']}")
                return attachment['url']
    sys.exit(f'No "{ANNUAL_PRISON}" file in the Offender management statistics quarterly collection')


def label(text):
    """A cell's text without its notes and spare spaces: 'TOTAL ROBBERY ' and 'Rape [note 28]' become 'TOTAL ROBBERY' and 'Rape'."""
    return ' '.join(re.sub(r'\[notes?[^\]]*\]', '', str(text)).split()) if text else ''


def number(text):
    """A cell's number; None where empty or '[x]', the ONS's mark for a figure that is not available."""
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def year_of(text):
    """The year a cell names, or None: 'Apr 2024 to Mar 2025' is 2024, 'Jan 1960 to Dec 1960' 1960.
    A cell that says more, such as a change compared with the previous year, names none.
    """
    found = FISCAL.fullmatch(label(text)) or CALENDAR.fullmatch(label(text))
    return int(found.group(1)) if found else None


def years_of(header):
    """{column: year} for the header's cells that name a year."""
    return {column: year_of(cell) for column, cell in enumerate(header) if year_of(cell)}


def recorded(folder):
    """{key: {year: offences}} from Table A5a, for every key of GROUPS, the year-ending-March columns only."""
    path = fetch(ons_file(APPENDIX), folder / 'appendix.xlsx')
    rows = spreadsheet.rows(path, sheet='Table A5a')
    header = next(row for row in rows if row and label(row[0]).startswith('Offence') and label(row[1]) == 'Offence category')
    years = years_of(header)
    by_label = {}
    for row in rows:
        if len(row) > 2 and row[0] is None and label(row[1]):
            if label(row[1]) in by_label:
                sys.exit(f'Table A5a names the group {label(row[1])!r} twice')
            by_label[label(row[1])] = row
    counts = {}
    for key, labels in GROUPS.items():
        counts[key] = {}
        for name in labels:
            if name not in by_label:
                sys.exit(f'No group {name!r} in Table A5a')
            for column, year in years.items():
                value = number(by_label[name][column])
                if value is not None:
                    counts[key].setdefault(year, value)
    return counts


def knife(folder):
    """{year: offences involving a knife or sharp instrument} from Table 21 of the weapons tables, the whole of England and Wales."""
    path = fetch(ons_file(WEAPONS), folder / 'weapons.xlsx')
    rows = spreadsheet.rows(path, sheet='Table 21')
    if 'knife' not in str(rows[0][0]) or not str(rows[1][0]).startswith('England and Wales,'):
        sys.exit('Table 21 of the weapons tables is no longer the knife offences of the whole of England and Wales')
    header = next(row for row in rows if row and row[0] == 'Selected offences')
    total = next(row for row in rows if row and label(row[0]) == KNIFE)
    return {year: number(total[column]) for column, year in years_of(header).items() if number(total[column]) is not None}


def homicides(folder):
    """{year: offences currently recorded as homicide} from Table 1 of the homicide tables.
    1997 is both a calendar year and April 1997 to March 1998 there: the April-to-March row comes last and wins.
    """
    path = fetch(ons_file(HOMICIDE), folder / 'homicide.xlsx')
    rows = spreadsheet.rows(path, sheet='Table 1')
    start = next(i for i, row in enumerate(rows) if row and row[0] == 'Year')
    if label(rows[start][1]) != 'Number of offences initially recorded as homicide' or \
            label(rows[start][3]) != 'Number of offences currently recorded as homicide':
        sys.exit('Table 1 of the homicide tables no longer has the columns this tool reads')
    series = {}
    for row in rows[start + 1:]:
        year = year_of(row[0]) if row else None
        if year is not None and len(row) >= 4 and number(row[3]) is not None:
            series[year] = number(row[3])
    return series


def prisoners(folder):
    """{year: the average of the 12 month-end prison populations} from Table 1.A.3 of the annual prison population."""
    path = fetch(prison_file(), folder / 'prison.ods')
    result = {}
    for row in ods.rows(path, sheet='Table_1_A_3'):
        found = re.fullmatch(r'Jan to Dec (\d{4})', str(row[0] or '')) if row else None
        if found and number(row[1]) is not None:
            result[int(found.group(1))] = number(row[1])
    if not result:
        sys.exit('No rows in Table_1_A_3 of the annual prison population')
    return result


def population(folder):
    """{year: people in England and Wales at mid-year} from Table 7 of the ONS's estimates from 1838."""
    path = fetch(ons_file(POPULATION, POPULATION_EDITION), folder / 'population.xlsx')
    people = {}
    for row in spreadsheet.rows(path, sheet='Table 7'):
        found = re.fullmatch(r'Mid-(\d{4})', str(row[0] or '')) if row else None
        if found and number(row[1]) is not None:
            people[int(found.group(1))] = number(row[1])
    if not people:
        sys.exit('No rows in Table 7 of the population estimates')
    return people


def main():
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        people = population(folder)
        counts = recorded(folder)
        counts['knife'] = knife(folder)
        counts['homicides'] = homicides(folder)
        counts['prison'] = prisoners(folder)
    rows = []
    for key, series in counts.items():
        for year, count in sorted(series.items()):
            if year <= LAST:
                rows.append((year, '', key, 'count', count))
                if year in people:
                    rows.append((year, '', key, 'rate', round(count / people[year] * 100000, 4)))
    rows.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    with open(OUT, 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['year', 'state', 'crime', 'measure', 'value'])
        writer.writerows(rows)
    print(f'{len(rows)} rows -> {OUT}')


if __name__ == '__main__':
    main()
