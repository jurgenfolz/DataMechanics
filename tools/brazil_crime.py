"""Builds Brazil's crime per year for Politics mode, for the whole country and by state.
It writes data/politics/brazil/crime.csv: the columns year, state (empty for the whole country), crime, measure and value.

Two federal sources, which Brazil's open data policy lets anyone reuse (Decreto 8.777/2016, art. 4):
- Deaths: the Ministry of Health's mortality records (SIM), from DATASUS's TabNet, from 1979.
  Its newest year is preliminary. ICD-9 codes the deaths until 1995, ICD-10 from 1996.
- Police records: the Ministry of Justice's Sinesp VDE ("Dados Nacionais de Segurança Pública"), from 2015.
  Before a state took up a category, it often sent zeros rather than nothing.
  So each police series starts in its first year with every state's figures (`first` in SINESP).
  A year counts for the country only when all 27 states sent every month, and for a state when it sent every month.
- Prisoners: the reports and files of Senappen, the national prison secretariat (formerly DEPEN), compiled by hand
  into data/politics/brazil/prison.csv with each row's source: people in prison cells and police cells from 2000, and
  by state the people in each state's prison cells from 2016.
Rates per 100,000 people are ours.
For the whole country they divide by the World Bank's population (the UN's World Population Prospects), the population
the site shows: one series for every year, by sex and by age.
For a state they divide by IBGE's projections (Revisão 2024), which give each state from 2000, so states start then.

Usage: .venv/bin/python tools/brazil_crime.py
"""

import csv
import html
import json
import re
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from xml.etree.ElementTree import iterparse

import spreadsheet  # tools/spreadsheet.py and tools/download.py, next to this file
from download import download

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'politics' / 'brazil' / 'crime.csv'
HEADERS = {'User-Agent': 'DataMechanics/1.0 (https://data-mechanics.com)'}
LAST = date.today().year - 1  # the last whole year
STATE_FIRST = 2000  # the first year of IBGE's state projections

# ---------- Deaths: SIM, through TabNet ----------
TABNET = 'http://tabnet.datasus.gov.br/cgi/'
# Each table of deaths from external causes, with its years.
ICD9 = ('sim/cnv/ext09uf.def', range(1979, 1996))
ICD10 = ('sim/cnv/ext10uf.def', range(1996, LAST + 1))
WOMEN = [('SSexo', '2')]
AT_HOME = [('SSexo', '2'), ('SLocal_ocorrência', '3')]  # women, killed at home
YOUNG = [('SFaixa_Etária', '5'), ('SFaixa_Etária', '6')]  # 15 to 19, and 20 to 29

# Our key -> the codes it counts in ICD-10 and in ICD-9 (first and last code of each range), the deaths it filters
# (TabNet's form fields) and the population of its rate.
HOMICIDE = {10: [('X85', 'Y09'), ('Y35', 'Y36')], 9: [('E960', 'E978')]}  # assaults and legal interventions
SIM = {
    'homicides': (HOMICIDE, [], 'all'),
    'firearm-homicides': ({10: [('X93', 'X95')], 9: [('E965', 'E965')]}, [], 'all'),  # assaults with a firearm
    'women-killed': (HOMICIDE, WOMEN, 'women'),
    'women-killed-at-home': (HOMICIDE, AT_HOME, 'women'),
    'young-people-killed': (HOMICIDE, YOUNG, 'young'),
    'unknown-intent': ({10: [('Y10', 'Y34')], 9: [('E980', 'E989')]}, [], 'all'),
}
SIM_BY_STATE = ['homicides', 'firearm-homicides', 'women-killed', 'unknown-intent']

# ---------- Police records: Sinesp VDE ----------
SINESP_URL = ('https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/estatistica/download/'
              'dnsp-base-de-dados/bancovde-{year}.xlsx/@@download/file')
STATES = 27
# Our key -> the events it adds up, the first year every state sent them, and the population of its rate.
SINESP = {
    'police-killings': (['Morte por intervenção de Agente do Estado'], 2020, 'all'),
    'officers-killed': (['Morte de Agente do Estado'], 2016, 'all'),
    'femicide': (['Feminicídio'], 2019, 'women'),
    'robbery-murder': (['Roubo seguido de morte (latrocínio)'], 2016, 'all'),
    'attempted-homicide': (['Tentativa de homicídio'], 2019, 'all'),
    'rape': (['Estupro', 'Estupro de vulnerável'], 2018, 'all'),
    'vehicle-robbery': (['Roubo de veículo'], 2021, 'all'),
    'vehicle-theft': (['Furto de veículo'], 2021, 'all'),
    'drug-trafficking': (['Tráfico de drogas'], 2018, 'all'),
    'firearms-seized': (['Arma de Fogo Apreendida'], 2021, 'all'),
}
# The states' own figures: the Federal Police and the Federal Highway Police appear in some years, which would make jumps.
STATE_POLICE = 'Estadual'
SPREADSHEET = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

# ---------- Prisoners, compiled by hand ----------
PRISON = ROOT / 'data' / 'politics' / 'brazil' / 'prison.csv'

# ---------- Population ----------
WORLD_BANK = 'https://api.worldbank.org/v2/country/BRA/indicator/{code}?format=json&per_page=200'
AGES = ('1519', '2024', '2529')  # five-year groups from 15 to 29, each a share of its sex
IBGE = 'https://ftp.ibge.gov.br/Projecao_da_Populacao/Projecao_da_Populacao_2024/projecoes_2024_tab4_indicadores.xlsx'


def get(url, data=None):
    request = urllib.request.Request(url, data=data, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=300) as response:
        return response.read()


def tabnet(table, filters, years=None, by_state=False):
    """Deaths by place of residence, from one of TabNet's tables: {row: {year: deaths}}.
    A row is an ICD category ('X85'), or with `by_state` a state's IBGE code (35 for São Paulo).
    """
    definition, every_year = table
    row = 'Unidade_da_Federação' if by_state else ('Categoria_CID9' if 'ext09' in definition else 'Categoria_CID10')
    files = [('Arquivos', f'extuf{year % 100:02d}.dbf') for year in (years or every_year)]
    form = [('Linha', row), ('Coluna', 'Ano_do_Óbito'), ('Incremento', 'Óbitos_p/Residênc'),
            *files, *filters, ('formato', 'prn'), ('mostre', 'Mostra')]
    page = get(f'{TABNET}tabcgi.exe?{definition}', urllib.parse.urlencode(form, encoding='latin-1').encode('ascii'))
    found = re.search(r'<PRE>(.*?)</PRE>', page.decode('latin-1'), re.S | re.I)
    if not found:
        sys.exit(f'TabNet gave no table for {definition} {filters}')
    # Unescape first: an entity such as &ccedil; carries a ';' that would split a cell.
    lines = [html.unescape(line) for line in found.group(1).strip().splitlines() if line.strip() not in ('', '&')]
    head = [cell.strip('"') for cell in lines[0].split(';')]
    deaths = {}
    for line in lines[1:]:
        cells = [cell.strip('"') for cell in line.split(';')]
        key = re.match(r'\d{2} ' if by_state else r'[A-Z]\d{2,3}', cells[0])
        if key:
            deaths[key.group(0).strip()] = {int(year): 0 if value == '-' else int(value)
                                            for year, value in zip(head[1:], cells[1:]) if year.isdigit()}
    return deaths


def counted(code, ranges):
    return any(first <= code[:len(first)] <= last for first, last in ranges)


def sim():
    """{key: {year: deaths}} for SIM's series, ICD-9 years first."""
    found = defaultdict(dict)
    for icd, table in [(9, ICD9), (10, ICD10)]:
        tables = {}  # one query per filter, shared by the series that use it
        for key, (codes, filters, _) in SIM.items():
            deaths = tables.setdefault(tuple(filters), tabnet(table, filters))
            for code, years in deaths.items():
                if counted(code, codes[icd]):
                    for year, count in years.items():
                        found[key][year] = found[key].get(year, 0) + count
    return found


def sim_by_state(states):
    """{key: {(state, year): deaths}} for SIM_BY_STATE, from STATE_FIRST. `states` maps IBGE codes to abbreviations."""
    definition, _ = ICD10
    # By state, TabNet takes the categories as a filter of the form's own numbers for them.
    form = get(f'{TABNET}deftohtm.exe?{definition}').decode('latin-1')
    options = form[form.find('SCategoria_CID10'):]
    options = re.findall(r'<option[^>]*value="?(\d+)"?[^>]*>\s*([A-Z]\d{2})', options[:options.find('</select>')], re.I)
    found = defaultdict(dict)
    for key in SIM_BY_STATE:
        codes, filters, _ = SIM[key]
        categories = [('SCategoria_CID10', number) for number, code in options if counted(code, codes[10])]
        deaths = tabnet(ICD10, categories + filters, range(STATE_FIRST, LAST + 1), by_state=True)
        for code, years in deaths.items():
            for year, count in years.items():
                found[key][states[code], year] = count
    return found


def sinesp(folder):
    """{key: {(state, year): count}} for the police series, the whole country as state ''.
    A state counts in a year when it sent every month, the country when every state did.
    """
    events = {event for names, _, _ in SINESP.values() for event in names}
    totals = defaultdict(float)  # (event, state, year) -> count
    sent = defaultdict(set)  # (event, state, year) -> months with a figure
    for year in range(min(first for _, first, _ in SINESP.values()), LAST + 1):
        path = download(SINESP_URL.format(year=year), Path(folder) / f'sinesp-{year}.xlsx')
        for row in sheet(path):
            if row.get('evento') not in events or row.get('abrangencia') != STATE_POLICE:
                continue
            # A victims' event fills total_vitima, the others total: never both.
            value = row.get('total_vitima') or row.get('total')
            if value in (None, ''):
                continue
            when = month(row['data_referencia'])
            totals[row['evento'], row['uf'], when.year] += float(value)
            sent[row['evento'], row['uf'], when.year].add(when.month)
        path.unlink()
    states = {state for _, state, _ in sent}
    found = defaultdict(dict)
    for key, (names, first, _) in SINESP.items():
        for year in range(first, LAST + 1):
            whole = [state for state in states if all(len(sent[event, state, year]) == 12 for event in names)]
            for state in whole:
                found[key][state, year] = sum(totals[event, state, year] for event in names)
            if len(whole) == STATES:
                found[key]['', year] = sum(found[key][state, year] for state in whole)
    return found


def sheet(path):
    """The rows of a Sinesp workbook's only sheet, as dicts by header. Its cells hold their text inline."""
    with zipfile.ZipFile(path) as book, book.open('xl/worksheets/sheet1.xml') as file:
        header = None
        for _, element in iterparse(file):
            if element.tag != SPREADSHEET + 'row':
                continue
            cells = {}
            for cell in element.findall(SPREADSHEET + 'c'):
                column = re.match(r'[A-Z]+', cell.get('r')).group(0)
                if cell.get('t') == 'inlineStr':
                    cells[column] = ''.join(t.text or '' for t in cell.iter(SPREADSHEET + 't')).strip()
                else:
                    value = cell.find(SPREADSHEET + 'v')
                    cells[column] = None if value is None else value.text
            element.clear()
            if header is None:
                header = cells
            else:
                yield {name: cells.get(column) for column, name in header.items()}


def month(value):
    """A Sinesp month: an Excel date number, or a text date."""
    try:
        return date(1899, 12, 30) + timedelta(days=int(float(value)))
    except ValueError:
        return date.fromisoformat(value[:10])


def prison():
    """{(state, year): people} from PRISON, the whole country as state ''."""
    with open(PRISON, encoding='utf-8', newline='') as file:
        return {(row['state'], int(row['year'])): int(row['people']) for row in csv.DictReader(file)}


def population():
    """Brazil's people by year, from the World Bank: {'all', 'women', 'young' (15 to 29): {year: people}}."""
    series = {}
    for code in ['SP.POP.TOTL', 'SP.POP.TOTL.FE.IN', 'SP.POP.TOTL.MA.IN',
                 *(f'SP.POP.{ages}.{sex}.5Y' for ages in AGES for sex in ('FE', 'MA'))]:
        _, rows = json.loads(get(WORLD_BANK.format(code=code)))
        series[code] = {int(row['date']): row['value'] for row in rows if row['value'] is not None}
    people = defaultdict(dict)
    for year, total in series['SP.POP.TOTL'].items():
        people['all'][year] = total
        people['women'][year] = series['SP.POP.TOTL.FE.IN'][year]
        # Each five-year group is a share (%) of its sex.
        people['young'][year] = sum(series[f'SP.POP.{ages}.{sex}.5Y'][year] / 100 * series[f'SP.POP.TOTL.{sex}.IN'][year]
                                    for ages in AGES for sex in ('FE', 'MA'))
    return people


def state_population(folder):
    """Each state's people by year, from IBGE: ({'all', 'women': {(state, year): people}}, {IBGE code: state})."""
    path = Path(folder) / 'ibge.xlsx'
    path.write_bytes(get(IBGE))
    people, states = defaultdict(dict), {}
    for row in spreadsheet.rows(path):
        # Year, IBGE code, abbreviation, name, people, men, women; the country (BR) and its regions have codes under 11.
        if len(row) > 6 and str(row[0]).isdigit() and str(row[1]).isdigit() and int(row[1]) >= 11:
            year, state = int(row[0]), row[2]
            states[row[1]] = state
            people['all'][state, year] = int(row[4])
            people['women'][state, year] = int(row[6])
    return people, states


def main():
    people = population()
    with tempfile.TemporaryDirectory() as folder:
        state_people, states = state_population(folder)
        counts = {key: {('', year): count for year, count in years.items()} for key, years in sim().items()}
        for key, found in sim_by_state(states).items():
            counts[key].update(found)
        counts.update(sinesp(folder))
    counts['prison'] = prison()
    bases = {key: base for key, (*_, base) in {**SIM, **SINESP}.items()} | {'prison': 'all'}
    rows = []
    for key in [*SIM, *SINESP, 'prison']:
        for (state, year), count in sorted(counts[key].items()):
            rows.append([year, f'BR-{state}' if state else '', key, 'count', f'{count:.10g}'])
            people_then = state_people[bases[key]].get((state, year)) if state else people[bases[key]].get(year)
            if people_then and (not state or year >= STATE_FIRST):
                rows.append([year, f'BR-{state}' if state else '', key, 'rate', f'{count / people_then * 100_000:.6g}'])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['year', 'state', 'crime', 'measure', 'value'])
        writer.writerows(rows)
    print(f'{OUT.relative_to(ROOT)}: {len(rows)} rows')


if __name__ == '__main__':
    main()
