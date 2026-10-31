"""Builds France's crime per year for Politics mode, for the whole country and by département.
It writes data/politics/france/crime.csv: the columns year, state (empty for the whole country), crime, measure and value.

Sources, all under the Licence Ouverte 2.0 (Etalab), which asks only that the source and its update date be named:
- Police and gendarmerie records: the Interior Ministry's statistical service (SSMSI) on data.gouv.fr.
  Its base by département gives 18 indicators for the 101 départements from 2016 (BASES).
  Its base of time series gives the same indicators for the whole country, and homicides from 2008 (CHRONO).
  The whole country's figure is the SSMSI's own, not the sum of the départements: fraud is counted where the victim
  lives, and drug suspects once per territory, so their sums differ from the national figure.
- Prisoners: the Ministry of Justice's yearly series of people under its charge (PPSMJ), people held in prison on
  1 January of each year, from 1990, with the prisons' capacity. We count a 1 January under the year before.
- Population: INSEE's estimates on 1 January, by département from 1975 (INSEE). A year's rate divides by the average
  of its 1 January and the next, our mid-year estimate.

Usage: .venv/bin/python tools/france_crime.py
"""

import csv
import io
import json
import re
import sys
import tempfile
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

import spreadsheet  # tools/spreadsheet.py and tools/download.py, next to this file
from download import download

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'politics' / 'france' / 'crime.csv'
HEADERS = {'User-Agent': 'DataMechanics/1.0 (https://data-mechanics.com)'}
LAST = date.today().year - 1  # the last whole year

# The data.gouv.fr datasets: their id, and the resource (by its title's start and format) the tool reads.
DATAGOUV = 'https://www.data.gouv.fr/api/1/datasets/{id}/'
BASES = ('621df2954fa5a3b5a023e23c', 'DEP - ', 'csv')  # bases statistiques ... de la délinquance enregistrée
CHRONO = ('62b02e970a264df3467b6c42', 'serieschrono', 'csv')  # base des séries chronologiques
PPSMJ = 'https://www.justice.gouv.fr/sites/default/files/2026-03/series_statistiques_ppsmj.xlsx'
INSEE = 'https://api.insee.fr/melodi/file/DS_ESTIMATION_POPULATION/DS_ESTIMATION_POPULATION_CSV_FR'

# Our key -> the indicator in the base by département, and the national series in the base of time series, picked by
# the values of its columns. A key with two national series takes the first where it has a value.
CHRONO_COLUMNS = ('Indicateur', 'Sous_indicateur', 'Nomenclature', 'Declinaison', 'Unite_de_compte', 'Detail_complementaire')
HOMICIDES = "Homicides et tentatives d'homicide"
PHYSICAL = ('Violences physiques', 'Ensemble des lieux', 'Non Renseigné')
CRIMES = {
    'homicides': ('Homicides', [
        (HOMICIDES, 'Homicides', 'Non Renseigné', 'Non Renseigné', 'Victimes', 'Y compris attentats terroristes'),
        (HOMICIDES, 'Non Renseigné', 'Non Renseigné', 'Non Renseigné', 'Victimes',
         "Pas de distinction possible des victimes d'attentats (hormis 2015)"),
    ]),
    'attempted-homicide': ("Tentatives d'homicide", [
        (HOMICIDES, "Tentatives d'homicide", 'Non Renseigné', 'Non Renseigné', 'Victimes', 'Non Renseigné')]),
    'domestic-violence': ('Violences physiques intrafamiliales', [
        (*PHYSICAL, 'Ensemble des violences physiques intrafamiliales', 'Victimes', 'Non Renseigné')]),
    'assault': ('Violences physiques hors cadre familial', [
        (*PHYSICAL, 'Ensemble des violences physiques hors cadre familial', 'Victimes', 'Non Renseigné')]),
    'sexual-violence': ('Violences sexuelles', [
        ('Violences sexuelles', 'Ensemble des lieux', 'Nomenclature française des infractions (NFI)',
         'Ensemble des violences sexuelles', 'Victimes', 'Non Renseigné')]),
    'armed-robbery': ('Vols avec armes', [
        ('Vols et tentatives de vols avec violence', 'Vols avec armes', 'Non Renseigné', 'Non Renseigné', 'Infractions',
         'Non Renseigné')]),
    'robbery': ('Vols violents sans arme', [
        ('Vols et tentatives de vols avec violence', 'Vols violents sans arme', 'Non Renseigné', 'Non Renseigné',
         'Infractions', 'Non Renseigné')]),
    'theft': ('Vols sans violence contre des personnes', [
        ('Vols et tentatives de vols sans violence', 'Non Renseigné', 'Non Renseigné', 'Non Renseigné', 'Victimes',
         'Non Renseigné')]),
    'burglary': ('Cambriolages de logement', [
        ('Cambriolages et tentatives', 'Logements (résidences principales et secondaires)', 'Non Renseigné',
         'Non Renseigné', 'Infractions', 'Non Renseigné')]),
    'vehicle-theft': ('Vols de véhicule', [
        ('Vols et tentatives de vols liés aux véhicules', 'Vols de véhicule', 'Non Renseigné', 'Non Renseigné',
         'Véhicules', 'Non Renseigné')]),
    'theft-from-vehicles': ('Vols dans les véhicules', [
        ('Vols et tentatives de vols liés aux véhicules', 'Vols dans les véhicules', 'Non Renseigné', 'Non Renseigné',
         'Véhicules', 'Non Renseigné')]),
    'vehicle-parts-theft': ("Vols d'accessoires sur véhicules", [
        ('Vols et tentatives de vols liés aux véhicules', "Vols d'accessoires sur véhicules", 'Non Renseigné',
         'Non Renseigné', 'Véhicules', 'Non Renseigné')]),
    'criminal-damage': ('Destructions et dégradations volontaires', [
        ('Destructions et dégradations volontaires', 'Non Renseigné', 'Non Renseigné', 'Non Renseigné', 'Infractions',
         'Non Renseigné')]),
    'drug-use': ('Usage de stupéfiants', [
        ('Infractions à la législation sur les stupéfiants', 'Usage de stupéfiants', 'Non Renseigné', 'Non Renseigné',
         'Mis en cause', 'Non Renseigné')]),
    'drug-trafficking': ('Trafic de stupéfiants', [
        ('Infractions à la législation sur les stupéfiants', 'Trafic de stupéfiants', 'Non Renseigné', 'Non Renseigné',
         'Mis en cause', 'Non Renseigné')]),
    'fraud': ('Escroqueries et fraudes aux moyens de paiement', [
        ('Escroqueries et les fraudes aux moyens de paiements', 'Ensemble des lieux', 'Non Renseigné', 'Non Renseigné',
         'Victimes', 'Non Renseigné')]),
}

# INSEE's département codes -> ISO 3166-2 as Natural Earth writes it (the overseas départements by their letters).
OVERSEAS = {'971': 'FR-GP', '972': 'FR-MQ', '973': 'FR-GF', '974': 'FR-RE', '976': 'FR-YT'}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=120) as response:
        return response.read()


def resource(dataset):
    """The address of a dataset's resource whose title starts as `BASES` or `CHRONO` say, from data.gouv.fr's API."""
    dataset_id, title, extension = dataset
    for found in json.loads(get(DATAGOUV.format(id=dataset_id)))['resources']:
        if found['title'].startswith(title) and found['format'] == extension:
            return found['url']
    sys.exit(f'No resource starting with {title!r} in dataset {dataset_id}')


def number(text):
    """A number as the files write it: '45 420', '0,0078318' or '124,0 %'; None where empty."""
    if text is None:
        return None
    digits = re.sub(r'[^\d,.-]', '', str(text)).replace(',', '.')
    return float(digits) if digits not in ('', '-', '.') else None


def by_departement(folder):
    """{(key, code, year): count} from the base by département, for every key of CRIMES."""
    path = download(resource(BASES), folder / 'dep.csv')
    wanted = {label: key for key, (label, _) in CRIMES.items()}
    counts = {}
    with open(path, encoding='utf-8-sig', newline='') as file:
        for row in csv.DictReader(file, delimiter=';'):
            key = wanted.get(row['indicateur'])
            if key:
                code = OVERSEAS.get(row['Code_departement'], f"FR-{row['Code_departement']}")
                counts[key, code, int(row['annee'])] = number(row['nombre'])
    return counts


def national(folder):
    """{key: {year: count}} for the whole country, from the base of time series."""
    path = download(resource(CHRONO), folder / 'chrono.csv')
    series = {}
    with open(path, encoding='latin-1', newline='') as file:
        for row in csv.DictReader(file, delimiter=';'):
            if row['Zone_geographique'] != 'France' or row['Periodicite'] != 'Annuelle' or row['Statistique'] != 'Nombre':
                continue
            picked = tuple(row[column] for column in CHRONO_COLUMNS)
            value = number(row['Valeurs'])
            if value is not None and row['Unite_temps'].isdigit():
                series.setdefault(picked, {})[int(row['Unite_temps'])] = value
    counts = {}
    for key, (_, selectors) in CRIMES.items():
        counts[key] = {}
        for selector in selectors:
            if selector not in series:
                sys.exit(f'No national series for {key}: {selector}')
            for year, value in series[selector].items():
                counts[key].setdefault(year, value)
    return counts


def prisoners(folder):
    """{year: (people held in prison, occupancy in %)} from the Ministry of Justice's Tableau 3, a 1 January under the year before."""
    path = download(PPSMJ, folder / 'ppsmj.xlsx')
    result = {}
    for row in spreadsheet.rows(path, sheet='Tableau 3'):
        if row and str(row[0]).strip().isdigit() and len(row) >= 6:
            result[int(row[0]) - 1] = (number(row[2]), number(row[5]))
    if not result:
        sys.exit('No rows in Tableau 3 of the prison series')
    return result


def population(folder):
    """{'FRA' or an ISO 3166-2 code: {year: people on 1 January}} from INSEE's estimates."""
    path = download(INSEE, folder / 'insee.zip')
    people = {}
    with zipfile.ZipFile(path) as book:
        name = next(name for name in book.namelist() if name.endswith('_data.csv'))
        with book.open(name) as raw:
            for row in csv.DictReader(io.TextIOWrapper(raw, encoding='utf-8-sig'), delimiter=';'):
                if row['EP_MEASURE'] != 'POP_JAN_1ST' or row['AGE'] != '_T' or row['SEX'] != '_T':
                    continue
                if row['GEO'] == 'F':
                    code = 'FRA'
                elif row['GEO_OBJECT'] == 'DEP':
                    code = OVERSEAS.get(row['GEO'], f"FR-{row['GEO']}")
                else:
                    continue
                people.setdefault(code, {})[int(row['TIME_PERIOD'])] = float(row['OBS_VALUE'])
    return people


def mid_year(people, year):
    """The average of the people on 1 January of `year` and of the next, or None."""
    if year in people and year + 1 in people:
        return (people[year] + people[year + 1]) / 2
    return None


def main():
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        people = population(folder)
        counts = national(folder)
        departements = by_departement(folder)
        held = prisoners(folder)
    rows = []

    def add(year, state, crime, count, per=None):
        rows.append((year, state, crime, 'count', count))
        rate = mid_year(people[per or 'FRA'], year) if per != 'none' else None
        if rate:
            rows.append((year, state, crime, 'rate', round(count / rate * 100000, 4)))

    for key, series in counts.items():
        for year, count in sorted(series.items()):
            if year <= LAST:
                add(year, '', key, count)
    for (key, code, year), count in sorted(departements.items()):
        if year <= LAST and count is not None:
            add(year, code, key, count, per=code)
    for year, (count, occupancy) in sorted(held.items()):
        if year <= LAST and count is not None:
            add(year, '', 'prison', count)
            if occupancy is not None:
                rows.append((year, '', 'prison', 'occupancy', occupancy))
    rows.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    with open(OUT, 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['year', 'state', 'crime', 'measure', 'value'])
        writer.writerows(rows)
    print(f'{len(rows)} rows -> {OUT}')


if __name__ == '__main__':
    main()
