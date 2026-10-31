"""Builds Italy's crime per year for Politics mode, for the whole country and by province.
It writes data/politics/italy/crime.csv: the columns year, state (empty for the whole country), crime, measure and value.

Sources:
- Crimes reported by the police to the courts, from Istat's data warehouse (SDMX API, CC BY 4.0), 2006 onward:
  counts (DELITTIPS_1) for Italy and 106 provinces.
  Sardinia's four provinces keep their borders of 2001 in these data, so geo_state merges Natural Earth's eight into them,
  and Cagliari's population adds Sud Sardegna's, carved out of it in 2016.
- Women killed: homicide victims by sex (AUTVITTPS_8), 2007 onward, for the whole country.
- Prisoners: the Ministry of Justice's series of prisoners present on 31 December, 1991 onward, an HTML table on
  giustizia.it. The ministry allows reuse for non-commercial ends, naming the source.
- Population: Istat's residents on 1 January, the reconstructed series 2001 to 2019 and the post-census series from
  2019, for the whole country and the provinces. Rates per 100,000 are ours: a year's rate divides by the average of
  its 1 January and the next. The women's rate divides by the World Bank's women of Italy (the UN's World Population
  Prospects), a mid-year figure that answers when Istat's server does not.

Usage: .venv/bin/python tools/italy_crime.py
"""

import csv
import io
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'politics' / 'italy' / 'crime.csv'
HEADERS = {'User-Agent': 'DataMechanics/1.0 (https://data-mechanics.com)', 'Accept': 'application/vnd.sdmx.data+csv;version=1.0.0'}
LAST = date.today().year - 1  # the last whole year

SDMX = 'https://esploradati.istat.it/SDMXWS/rest/data/{flow}/{key}'
COUNTS = ('73_67_DF_DCCV_DELITTIPS_1', 'A..CRIMEN..9.YRDUR')
WOMEN_KILLED = ('73_230_DF_DCCV_AUTVITTPS_8', 'A.IT.VICTIM.INTENHOM.2.TOTAL.TOTAL.')
# Residents on 1 January: 2001 to 2019 reconstructed after the 2011 census, then the series after the 2021 census.
# Each key takes every area (the second position) and both sexes (9).
POPULATION = [
    ('164_164_DF_DCIS_RICPOPRES2011_1', 'A..JAN.TOTAL.9.TOTAL'),
    ('22_289_DF_DCIS_POPRES1_1', 'A..JAN.9.TOTAL.99'),
]
WORLD_BANK_WOMEN = 'https://api.worldbank.org/v2/country/ITA/indicator/SP.POP.TOTL.FE.IN?format=json&per_page=200'
SUD_SARDEGNA = 'IT111'  # counted with Cagliari (ITG27), whose borders of 2001 held it
PRISONERS = 'https://www.giustizia.it/giustizia/it/mg_1_14_1.page?contentId=SST165666'

# Istat's crime codes -> our keys.
CRIMES = {
    'TOT': 'all',
    'INTENHOM': 'homicides',
    'ATTEMPHOM': 'attempted-homicide',
    'RAPE': 'sexual-violence',
    'CULPINJU': 'bodily-harm',
    'BLOWS': 'battery',
    'MENACE': 'threats',
    'ROBBER': 'robbery',
    'STREETROB': 'street-robbery',
    'THEFT': 'theft',
    'BURGTHEF': 'burglary',
    'PICKTHEF': 'pickpocketing',
    'BAGTHEF': 'bag-snatching',
    'SHOPTHEF': 'shop-theft',
    'CARTHEF': 'car-theft',
    'EXTORT': 'extortion',
    'SWINCYB': 'fraud',
    'DAMAGE': 'criminal-damage',
    'DRUG': 'drugs',
    'MAFIASS': 'mafia-association',
}
# Istat's province codes -> ISO 3166-2, as Natural Earth writes it (Sardinia's four at their borders of 2001).
PROVINCES = {
    'IT108': 'IT-MB', 'IT109': 'IT-FM', 'IT110': 'IT-BT', 'ITC11': 'IT-TO', 'ITC12': 'IT-VC', 'ITC13': 'IT-BI',
    'ITC14': 'IT-VB', 'ITC15': 'IT-NO', 'ITC16': 'IT-CN', 'ITC17': 'IT-AT', 'ITC18': 'IT-AL', 'ITC20': 'IT-AO',
    'ITC31': 'IT-IM', 'ITC32': 'IT-SV', 'ITC33': 'IT-GE', 'ITC34': 'IT-SP', 'ITC41': 'IT-VA', 'ITC42': 'IT-CO',
    'ITC43': 'IT-LC', 'ITC44': 'IT-SO', 'ITC45': 'IT-MI', 'ITC46': 'IT-BG', 'ITC47': 'IT-BS', 'ITC48': 'IT-PV',
    'ITC49': 'IT-LO', 'ITC4A': 'IT-CR', 'ITC4B': 'IT-MN', 'ITD10': 'IT-BZ', 'ITD20': 'IT-TN', 'ITD31': 'IT-VR',
    'ITD32': 'IT-VI', 'ITD33': 'IT-BL', 'ITD34': 'IT-TV', 'ITD35': 'IT-VE', 'ITD36': 'IT-PD', 'ITD37': 'IT-RO',
    'ITD41': 'IT-PN', 'ITD42': 'IT-UD', 'ITD43': 'IT-GO', 'ITD44': 'IT-TS', 'ITD51': 'IT-PC', 'ITD52': 'IT-PR',
    'ITD53': 'IT-RE', 'ITD54': 'IT-MO', 'ITD55': 'IT-BO', 'ITD56': 'IT-FE', 'ITD57': 'IT-RA', 'ITD58': 'IT-FC',
    'ITD59': 'IT-RN', 'ITE11': 'IT-MS', 'ITE12': 'IT-LU', 'ITE13': 'IT-PT', 'ITE14': 'IT-FI', 'ITE15': 'IT-PO',
    'ITE16': 'IT-LI', 'ITE17': 'IT-PI', 'ITE18': 'IT-AR', 'ITE19': 'IT-SI', 'ITE1A': 'IT-GR', 'ITE21': 'IT-PG',
    'ITE22': 'IT-TR', 'ITE31': 'IT-PU', 'ITE32': 'IT-AN', 'ITE33': 'IT-MC', 'ITE34': 'IT-AP', 'ITE41': 'IT-VT',
    'ITE42': 'IT-RI', 'ITE43': 'IT-RM', 'ITE44': 'IT-LT', 'ITE45': 'IT-FR', 'ITF11': 'IT-AQ', 'ITF12': 'IT-TE',
    'ITF13': 'IT-PE', 'ITF14': 'IT-CH', 'ITF21': 'IT-IS', 'ITF22': 'IT-CB', 'ITF31': 'IT-CE', 'ITF32': 'IT-BN',
    'ITF33': 'IT-NA', 'ITF34': 'IT-AV', 'ITF35': 'IT-SA', 'ITF41': 'IT-FG', 'ITF42': 'IT-BA', 'ITF43': 'IT-TA',
    'ITF44': 'IT-BR', 'ITF45': 'IT-LE', 'ITF51': 'IT-PZ', 'ITF52': 'IT-MT', 'ITF61': 'IT-CS', 'ITF62': 'IT-KR',
    'ITF63': 'IT-CZ', 'ITF64': 'IT-VV', 'ITF65': 'IT-RC', 'ITG11': 'IT-TP', 'ITG12': 'IT-PA', 'ITG13': 'IT-ME',
    'ITG14': 'IT-AG', 'ITG15': 'IT-CL', 'ITG16': 'IT-EN', 'ITG17': 'IT-CT', 'ITG18': 'IT-RG', 'ITG19': 'IT-SR',
    'ITG25': 'IT-SS', 'ITG26': 'IT-NU', 'ITG27': 'IT-CA', 'ITG28': 'IT-OR',
}


def get(url, accept=None):
    headers = {**HEADERS, 'Accept': accept or HEADERS['Accept']}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=600) as response:
        return response.read()


def sdmx(flow, key):
    """The rows of an Istat dataflow, as dicts."""
    text = get(SDMX.format(flow=flow, key=key)).decode('utf-8-sig')
    return list(csv.DictReader(io.StringIO(text)))


def crimes(flow, key):
    """{(our key, ISO code or '' for Italy, year): value} for the crimes in CRIMES."""
    found = {}
    for row in sdmx(flow, key):
        crime = CRIMES.get(row['TYPE_CRIME'])
        area = '' if row['REF_AREA'] == 'IT' else PROVINCES.get(row['REF_AREA'])
        if crime and area is not None and row['OBS_VALUE']:
            found[crime, area, int(row['TIME_PERIOD'])] = float(row['OBS_VALUE'])
    return found


def population():
    """{'' for Italy or an ISO code: {year: people on 1 January}}.
    The first dataflow that has a year keeps it; Sud Sardegna's people are added to Cagliari's.
    """
    people = {}
    for flow, key in POPULATION:
        found = {}
        for row in sdmx(flow, key):
            if not row['OBS_VALUE']:
                continue
            if row['REF_AREA'] == 'IT':
                area = ''
            elif row['REF_AREA'] == SUD_SARDEGNA:
                area = 'IT-CA'
            else:
                area = PROVINCES.get(row['REF_AREA'])
            if area is not None:
                years = found.setdefault(area, {})
                year = int(row['TIME_PERIOD'])
                years[year] = years.get(year, 0) + float(row['OBS_VALUE'])
        for area, years in found.items():
            for year, value in years.items():
                people.setdefault(area, {}).setdefault(year, value)
    return people


def women():
    """{year: women in Italy at mid-year} from the World Bank."""
    _, rows = json.loads(get(WORLD_BANK_WOMEN, accept='application/json'))
    return {int(row['date']): float(row['value']) for row in rows if row['value'] is not None}


def mid_year(people, year):
    if year in people and year + 1 in people:
        return (people[year] + people[year + 1]) / 2
    return None


def prisoners():
    """{year: prisoners present on 31 December} from the ministry's table."""
    page = get(PRISONERS, accept='text/html').decode('utf-8', errors='replace')
    found = {}
    for match in re.finditer(r'31/12/(\d{4})</th>((?:\s*<td[^>]*>[^<]*</td>){4})', page):
        cells = re.findall(r'<td[^>]*>([^<]*)</td>', match.group(2))
        found[int(match.group(1))] = float(cells[3].replace('.', ''))
    if not found:
        sys.exit('No rows found in the prisoners table')
    return found


def main():
    people = population()
    women_by_year = women()
    rows = []
    for (crime, area, year), count in crimes(*COUNTS).items():
        if year > LAST:
            continue
        rows.append((year, area, crime, 'count', count))
        residents = mid_year(people.get(area, {}), year)
        if residents:
            rows.append((year, area, crime, 'rate', round(count / residents * 100000, 4)))
    for row in sdmx(*WOMEN_KILLED):
        year = int(row['TIME_PERIOD'])
        if row['OBS_VALUE'] and year <= LAST:
            count = float(row['OBS_VALUE'])
            rows.append((year, '', 'women-killed', 'count', count))
            if year in women_by_year:
                rows.append((year, '', 'women-killed', 'rate', round(count / women_by_year[year] * 100000, 4)))
    for year, count in prisoners().items():
        if year <= LAST:
            rows.append((year, '', 'prison', 'count', count))
            everyone = mid_year(people[''], year)
            if everyone:
                rows.append((year, '', 'prison', 'rate', round(count / everyone * 100000, 4)))
    rows.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    with open(OUT, 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['year', 'state', 'crime', 'measure', 'value'])
        writer.writerows(rows)
    print(f'{len(rows)} rows -> {OUT}')


if __name__ == '__main__':
    main()
