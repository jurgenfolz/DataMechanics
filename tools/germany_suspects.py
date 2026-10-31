"""Builds the Crime tab's data for Germany: the people of each nationality, and their crime suspects by kind of offence.
It writes data/politics/germany/population.csv and data/politics/germany/suspects.csv.

Suspects come from the police crime statistics of the Bundeskriminalamt (Polizeiliche Kriminalstatistik, PKS), table T62.
bka.de drops Python's connections, so download T62 by hand, from the address in T62 below.
It counts each suspect once a year for each kind of offence, by nationality.
People with German and another nationality count as German.
The tool takes the rows of the kinds of offence the page offers (politics.crime.OFFENCES), and the row of every offence.

People come from the Statistisches Bundesamt (Destatis), on 31 December of the same year.
Foreigners by nationality come from the Central Register of Foreigners (Ausländerzentralregister), GENESIS table 12521-0002.
GENESIS needs a login, so download that table by hand: 31 December of the year, by Staatsangehörigkeit, as CSV.
Germans come from the population update on the 2022 census, which the tool reads from Destatis's page.

A nationality found in only one of the two sources is left out, and so are the stateless and the unknown.
The row without a nationality is every foreign national together, the stateless and the unknown included.
Rerun the tool when the BKA publishes the next year's tables, with the addresses and the year below changed.

Usage: .venv/bin/python tools/germany_suspects.py path/to/T62.xlsx path/to/12521-0002_de.csv
"""

import csv
import html
import os
import re
import sys
import urllib.request
from pathlib import Path

import django

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import spreadsheet  # noqa: E402  (tools/spreadsheet.py, next to this file)
from geo.models import Country  # noqa: E402  (needs django.setup())
from politics.crime import counted  # noqa: E402

YEAR = 2025
T62 = ('https://www.bka.de/SharedDocs/Downloads/DE/Publikationen/PolizeilicheKriminalstatistik/2025/Bund/Tatverdaechtige/'
       'BU-TV-22-T62-TV-Staatsangehoerigkeiten_xls.xlsx?__blob=publicationFile&v=2')
GERMANS = ('https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/Bevoelkerungsstand/Tabellen/'
           'zensus-geschlecht-staatsangehoerigkeit-2025.html')
OUT = ROOT / 'data' / 'politics' / 'germany'
HEADERS = {'User-Agent': 'DataMechanics/1.0 (https://data-mechanics.com)'}

# The PKS's names that the register spells another way.
REGISTER_NAMES = {
    'Bolivien': 'Bolivien, Plurinationaler Staat',
    'Großbritannien/Nordirland': 'Vereinigtes Königreich',
    'Iran': 'Iran, Islamische Republik',
    'Kap Verde': 'Cabo Verde',
    'Korea, Volksrepublik': 'Korea, Demokratische Volksrepublik',
    'Laos': 'Laos, Demokratische Volksrepublik',
    'Mikronesien': 'Mikronesien, Föderierte Staaten von',
    'Moldau': 'Moldau, Republik',
    'Montenegro': 'Montenegro (ab 03.06.2006)',
    'St. Vincent': 'St. Vincent und die Grenadinen',
    'Sudan (ohne Südsudan)': 'Sudan (ohne Südsudan) (ab 09.07.2011)',
    'Swasiland': 'Eswatini',
    'Südsudan': 'Südsudan (ab 09.07.2011)',
    'Tschechische Republik': 'Tschechien',
    'USA': 'Vereinigte Staaten',
    'Venezuela': 'Venezuela, Bolivarische Republik',
    'Weißrussland (Belarus)': 'Belarus',
}

# The PKS's names that geo_country's German names (Natural Earth) spell another way.
COUNTRY_CODES = {
    'Botsuana': 'BWA',
    "Cote d'Ivoire": 'CIV',
    'Großbritannien/Nordirland': 'GBR',
    'Kongo, Demokratische Republik': 'COD',
    'Kongo, Republik': 'COG',
    'Korea, Republik': 'KOR',
    'Korea, Volksrepublik': 'PRK',
    'Moldau': 'MDA',
    'Russische Föderation': 'RUS',
    'Sao Tome und Principe': 'STP',
    'St. Vincent': 'VCT',
    'Sudan (ohne Südsudan)': 'SDN',
    'Swasiland': 'SWZ',
    'Timor-Leste': 'TLS',
    'Tschechische Republik': 'CZE',
    'USA': 'USA',
    'Weißrussland (Belarus)': 'BLR',
}
NOT_NATIONALITIES = {'Staatenlos', 'Ungeklärt', 'Ohne Angabe'}


def download(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def suspects(path):
    """T62's suspects: {name: {offence key: suspects}} for the keys the page uses, 'Nichtdeutsche insgesamt' among the names."""
    rows = spreadsheet.rows(path)
    names = next(row for row in rows if row and row[0] == 'Schlüssel')
    by_key = {row[0]: row for row in rows if row}
    missing = [key for key in counted() if key not in by_key]
    if missing:
        sys.exit(f'T62 has no row for {", ".join(missing)}: check politics.crime.OFFENCES against this year\'s table.')
    count = lambda value: int(float(value or 0))
    return {name: {key: count(by_key[key][i]) for key in counted()} for i, name in enumerate(names) if i >= 3 and name}


def register(path):
    """The register's foreigners on 31 December: {name: people}, with 'Insgesamt' for every foreign national."""
    people = {}
    with open(path, encoding='utf-8-sig') as file:
        for line in csv.reader(file, delimiter=';'):
            if len(line) > 6 and line[0] == f'31.12.{YEAR}' and line[6].isdigit():
                people[line[1]] = int(line[6])
    return people


def germans():
    """Germans on 31 December, from Destatis's table of the population update by nationality."""
    page = download(GERMANS).decode('utf-8')
    cells = lambda row: [html.unescape(re.sub(r'<[^>]+>', '', cell)).strip()
                         for cell in re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row, re.S)]
    rows = [cells(row) for row in re.findall(r'<tr.*?</tr>', page, re.S)]
    column = next(row for row in rows if f'31.12.{YEAR}' in row).index(f'31.12.{YEAR}')
    value = next(row for row in rows if row and row[0] == 'Deutsche')[column]
    return int(re.sub(r'\D', '', value))


def main(t62, register_csv):
    found = suspects(t62)
    people = register(register_csv)
    codes = {country.name_de: country.iso3 for country in Country.objects.exclude(name_de='')}
    # Germans and every foreign national together first, then each nationality.
    nationalities = [('DEU', 'Deutsche', germans(), found.pop('Deutschland')),
                     ('', 'Nichtdeutsche insgesamt', people['Insgesamt'], found.pop('Nichtdeutsche insgesamt'))]
    left_out = []
    for name, counts in found.items():
        population = people.get(REGISTER_NAMES.get(name, name))
        code = COUNTRY_CODES.get(name) or codes.get(name)
        if name in NOT_NATIONALITIES or not population or not code:
            left_out.append(name)
            continue
        nationalities.append((code, name, population, counts))
    nationalities[2:] = sorted(nationalities[2:], key=lambda row: -row[2])
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / 'population.csv', 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['year', 'nationality', 'source_name', 'population'])
        writer.writerows([YEAR, code, name, population] for code, name, population, _ in nationalities)
    # A kind of offence without suspects of a nationality is left out of its rows.
    with open(OUT / 'suspects.csv', 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['year', 'nationality', 'offence', 'suspects'])
        rows = [[YEAR, code, key, n] for code, _, _, counts in nationalities for key, n in counts.items() if n]
        writer.writerows(rows)
    print(f'population.csv: {len(nationalities)} rows; suspects.csv: {len(rows)} rows; left out: {", ".join(left_out) or "none"}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
