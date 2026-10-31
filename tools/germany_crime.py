"""Builds Germany's crime per year for Politics mode, for the whole country and by Land, from the police crime statistics.
It writes data/politics/germany/crime.csv: the columns year, state (empty for the whole country), crime, measure and value.

The Bundeskriminalamt (BKA) publishes the Polizeiliche Kriminalstatistik (PKS) each spring, with time series of every
offence key (FILES). The tool downloads them with curl (tools/download.py): bka.de stalls and resets connections, and drops Python's.
politics/crime_series.py names the kinds of crime and their measures; CRIMES below says where each comes from.

Each kind of crime starts in the first year that compares with the years after it (`first` in CRIMES):
- 1993, the first year of all of Germany. 1987 to 1992 cover the old Länder, with all of Berlin from 1991.
- A law that changed what the police count as the offence: sexual offences (2017 and 2018), assaults on officers (2018),
  child sexual abuse (2022).
- A change in how the police count: fraud (1994), cybercrime (2016), suspects counted once each a year (2009).
- Suspects per 100,000 residents start in 2013, the first year on the 2011 census.
  The census found 13% fewer foreign residents than the old count, which raised their rate by about 14% at once.

The Länder come from each edition's Länder table (LAENDER), which has no time series: each Land's cases, cases per
100,000 people and clearance rate by offence key. They start in 2014, the first edition the tool can read (2013's is
an old binary .xls), or later where the kind of crime starts later. The 16 Länder add up to the whole country.

Usage: .venv/bin/python tools/germany_crime.py
Rerun it when the BKA publishes the next year's tables, with YEAR and the addresses in FILES changed.
"""

import csv
import re
import sys
import tempfile
from pathlib import Path

import spreadsheet  # tools/spreadsheet.py and tools/download.py, next to this file
from download import download

ROOT = Path(__file__).resolve().parent.parent

YEAR = 2025  # the PKS edition
OUT = ROOT / 'data' / 'politics' / 'germany' / 'crime.csv'
BASE = f'https://www.bka.de/SharedDocs/Downloads/DE/Publikationen/PolizeilicheKriminalstatistik/{YEAR}/Interpretation/'
# The time series this tool reads, from the page "Zeitreihen" of the PKS tables.
FILES = {
    # T01: cases, cases per 100,000 people (HZ), attempts, clearance rate and suspects, by offence key, from 1987.
    'cases': 'Faelle/T01-ZR-Bund-F%C3%A4lle_xls.xlsx?__blob=publicationFile&v=3',
    # T40 and T50: resident suspects aged 8 and over per 100,000 residents of the same age (TVBZ), German and not, from 2009.
    'german': 'Belastungszahlen/ZR-BZ-01-T40-TVBZ-insg-deutsch_xls.xlsx?__blob=publicationFile&v=3',
    'non_german': 'Belastungszahlen/ZR-BZ-01-T50-TVBZgesamtnichtdeutsch2009_xls.xlsx?__blob=publicationFile&v=3',
    # T91: victims, and victims per 100,000 people (OGZ), from 2000.
    'victims': 'Opfer/ZR-O-01-T91-Straftaten-insg_xls.xlsx?__blob=publicationFile&v=2',
    'victim_rate': 'Belastungszahlen/ZR-BZ-04-T91-OGZ-Straftaten-insg_xls.xlsx?__blob=publicationFile&v=2',
    # T92: victims by their relationship to the suspect, from 2000; its categories were redefined in 2014.
    'relationships': 'Opfer/ZR-O-04-T92-O-TV-Bez-Straftaten-insg_xls.xlsx?__blob=publicationFile&v=3',
}

FIRST = 1993  # all of Germany

# Our key -> the PKS key and the first year that compares with the years after it.
# Each gets the measures rate (HZ), cases and clearance (the clearance rate); murder and manslaughter also completed.
CRIMES = {
    'all': ('------', FIRST),
    'without-immigration-law': ('890000', FIRST),  # the key starts in 2005
    'violent': ('892000', FIRST),
    'murder': ('010000', FIRST),
    'manslaughter': ('020000', FIRST),
    'rape': ('111000', 2018),
    'sexual-harassment': ('114000', 2017),
    'child-sexual-abuse': ('131000', 2022),
    'robbery': ('210000', FIRST),
    'serious-bodily-harm': ('222000', FIRST),
    'bodily-harm': ('224000', FIRST),
    'assaults-on-officers': ('621000', 2018),
    'theft': ('****00', FIRST),
    'burglary': ('435*00', FIRST),
    'car-theft': ('***100', FIRST),
    'pickpocketing': ('*90*00', FIRST),
    'fraud': ('510000', 1994),
    'cybercrime': ('897000', 2016),
    'criminal-damage': ('674000', FIRST),
    'drugs': ('730000', FIRST),
    'immigration-law': ('725000', FIRST),
    'weapons': ('726200', FIRST),
}
COMPLETED = {'murder', 'manslaughter'}  # cases minus attempts

# Suspects of every offence but those against residence and asylum law, which only foreigners can break.
SUSPECTS = '890000'
SUSPECTS_FROM = 2009  # counted once each a year
RATES_FROM = 2013  # the 2011 census
# Victims of violent crime.
VICTIMS = '892000'
RELATIONSHIPS_FROM = 2014  # the categories were redefined

# Each edition's Länder table: T01 by Land. The addresses changed with the editions.
EDITIONS = 'https://www.bka.de/SharedDocs/Downloads/DE/Publikationen/PolizeilicheKriminalstatistik/'
LAENDER = {
    2025: '2025/Land/Faelle/LA-F-02-T01-Laender-Faelle-HZ_xls.xlsx?__blob=publicationFile&v=2',
    2024: '2024/Land/Faelle/LA-F-02-T01-Laender-Faelle-HZ_xls.xlsx?__blob=publicationFile&v=6',
    2023: '2023/Land/Faelle/LA-F-02-T01-Laender-Faelle-HZ_xls.xlsx?__blob=publicationFile&v=4',
    2022: '2022/Land/Faelle/LA-F-02-T01-Laender-Faelle-HZ_xls.xlsx?__blob=publicationFile&v=6',
    2021: '2021/Land/Faelle/LA-F-02-T01-Laender-Faelle-HZ_xls.xlsx?__blob=publicationFile&v=5',
    2020: '2020/Land/Faelle/LA-F-02-T01-Laender-Faelle-HZ_xls.xlsx?__blob=publicationFile&v=6',
    2019: '2019/Land/Faelle/LA-F-02-T01-Laender-Faelle-HZ_xls.xlsx?__blob=publicationFile&v=8',
    2018: '2018/BKATabellen/FaelleLaenderKreiseStaedte/BKA-LKS-F-01-T01-Laender_excel.xlsx?__blob=publicationFile&v=3',
    2017: '2017/BKATabellen/FaelleLaenderKreiseStaedte/BKA-LKS-F-01-T01-Laender_excel.xlsx?__blob=publicationFile&v=3',
    2016: '2016/BKATabellen/FaelleLaenderKreiseStaedte/BKA-LKS-F-01-T01-Laender_excel.xlsx?__blob=publicationFile&v=4',
    2015: '2015/BKATabellen/FaelleLaenderKreiseStaedte/tb01_FaelleGrundtabelleLaender_excel.xlsx?__blob=publicationFile&v=2',
    2014: '2014/BKATabellen/FaelleLaenderKreiseStaedte/tb01_FaelleGrundtabelleLaender_excel.xlsx?__blob=publicationFile&v=2',
}
# The Länder as the tables name them, with their ISO 3166-2 codes (geo_state).
LANDS = {
    'Baden-Württemberg': 'DE-BW', 'Bayern': 'DE-BY', 'Berlin': 'DE-BE', 'Brandenburg': 'DE-BB', 'Bremen': 'DE-HB',
    'Hamburg': 'DE-HH', 'Hessen': 'DE-HE', 'Mecklenburg-Vorpommern': 'DE-MV', 'Niedersachsen': 'DE-NI',
    'Nordrhein-Westfalen': 'DE-NW', 'Rheinland-Pfalz': 'DE-RP', 'Saarland': 'DE-SL', 'Sachsen': 'DE-SN',
    'Sachsen-Anhalt': 'DE-ST', 'Schleswig-Holstein': 'DE-SH', 'Thüringen': 'DE-TH',
}

# Columns of the time series, counted from 0.
T01 = {'cases': 3, 'rate': 4, 'attempts': 5, 'clearance': 9, 'suspects': 10}
TVBZ = 3  # residents aged 8 and over, every age together
VICTIMS_ALL = 3  # victims, men and women together
FAMILY = 6  # victims whose suspect is a spouse, partner or relative (from 2014)


def series(path, column):
    """One column of a time series: {(key, year): number}, without the empty cells and the few text ones."""
    found = {}
    for row in spreadsheet.rows(path):
        if len(row) <= column or not (row[0] and len(row[0]) == 6 and str(row[2] or '').isdigit()):
            continue
        try:
            found[row[0], int(row[2])] = float(row[column])
        except (TypeError, ValueError):
            pass  # empty, '-', or text where a number belongs (T01, key 143100, 2023)
    return found


def laender(path):
    """A Länder table: {(key, Land code): {'cases', 'rate', 'clearance'}}.
    Its columns move between editions, so they are found by the words of their headers.
    2024 gives the rate on both censuses: the 2022 census's, as the time series has.
    """
    table = spreadsheet.rows(path)
    clean = lambda text: re.sub(r'\s+', ' ', str(text or '').replace('\xa0', ' ')).strip()  # noqa: E731
    is_key = lambda text: re.fullmatch(r'[0-9*-]{6}', clean(text))  # noqa: E731
    start = next(i for i, row in enumerate(table) if row and clean(row[0]) in ('Schlüssel', 'Strft. Schl.'))
    first = next(i for i in range(start + 1, len(table)) if table[i] and is_key(table[i][0]))
    width = max(len(row) for row in table[start:first])
    # Each column's header, its lines joined; the line that numbers the columns is left out.
    head = [' '.join(clean(row[c]) for row in table[start:first] if c < len(row) and clean(row[c]) and not clean(row[c]).isdigit())
            for c in range(width)]
    rates = [c for c, words in enumerate(head) if 'HZ' in words]
    columns = {
        'land': next(c for c, words in enumerate(head) if words == 'Bundesland'),
        'cases': next(c for c, words in enumerate(head) if 'erfasste Fälle' in words and 'Versuch' not in words),
        'rate': next((c for c in rates if 'Zensus 22' in head[c]), rates[0]),
        'clearance': next(c for c, words in enumerate(head) if re.search(r'\bAQ\b', words)),
    }
    found = {}
    for row in table[first:]:
        land = LANDS.get(clean(row[columns['land']])) if row and is_key(row[0]) and len(row) > columns['land'] else None
        if land:
            found[clean(row[0]), land] = {measure: float(row[columns[measure]]) for measure in ('cases', 'rate', 'clearance')
                                          if row[columns[measure]] not in (None, '', '-')}
    return found


def rows(files):
    cases = {measure: series(files['cases'], column) for measure, column in T01.items()}
    out = []
    for crime, (key, first) in CRIMES.items():
        years = sorted(year for k, year in cases['cases'] if k == key and year >= first)
        if not years:
            sys.exit(f'T01 has no key {key} from {first}: check CRIMES against this year\'s table.')
        for year in years:
            out += [(year, '', crime, 'rate', cases['rate'][key, year]),
                    (year, '', crime, 'cases', cases['cases'][key, year]),
                    (year, '', crime, 'clearance', cases['clearance'][key, year])]
            if crime in COMPLETED:
                out.append((year, '', crime, 'completed', cases['cases'][key, year] - cases['attempts'][key, year]))
        for year in sorted(LAENDER):
            if year >= first:
                out += [(year, land, crime, measure, value) for (k, land), measures in sorted(files[year].items())
                        if k == key for measure, value in measures.items()]
    for measure, found in [('suspects', cases['suspects']), ('german', series(files['german'], TVBZ)),
                           ('non_german', series(files['non_german'], TVBZ))]:
        first = SUSPECTS_FROM if measure == 'suspects' else RATES_FROM
        out += [(year, '', 'suspects', measure, value) for (key, year), value in sorted(found.items())
                if key == SUSPECTS and year >= first]
    for measure, found, first in [('rate', series(files['victim_rate'], VICTIMS_ALL), 0),
                                  ('victims', series(files['victims'], VICTIMS_ALL), 0),
                                  ('family', series(files['relationships'], FAMILY), RELATIONSHIPS_FROM)]:
        out += [(year, '', 'victims', measure, value) for (key, year), value in sorted(found.items())
                if key == VICTIMS and year >= first]
    return out


def main():
    with tempfile.TemporaryDirectory() as folder:
        files = {name: download(BASE + file, Path(folder) / f'{name}.xlsx') for name, file in FILES.items()}
        # One download at a time: bka.de resets connections that come together.
        for year, file in LAENDER.items():
            files[year] = laender(download(EDITIONS + file, Path(folder) / f'laender-{year}.xlsx'))
        found = rows(files)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['year', 'state', 'crime', 'measure', 'value'])
        writer.writerows([year, state, crime, measure, f'{value:.10g}'] for year, state, crime, measure, value in found)
    print(f'{OUT.relative_to(ROOT)}: {len(found)} rows, {min(r[0] for r in found)} to {max(r[0] for r in found)}')


if __name__ == '__main__':
    main()
