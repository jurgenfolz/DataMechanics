"""Crime per year by kind of crime, for a country and its states, from data/politics/<country>/crime.csv.
Writes pol_crime_year.

Each file has the columns year, state (an ISO 3166-2 code, empty for the whole country), crime, measure and value.
tools/<country>_crime.py builds each file from the country's police, court and health statistics.
politics/crime_series.py names each country's kinds of crime and measures, and cites each one's source.
"""

import csv

from django.conf import settings

from politics.models import CrimeYear
from providers.load import Source, replace_rows

from . import COUNTRIES, DATA

# The page cites each kind of crime's own source (politics/crime_series.py); the load log needs one for the table.
SOURCE = Source('National police and health statistics, compiled by Data Mechanics', f'{settings.GITHUB_URL}/tree/master/data/politics')


def run():
    rows = []
    for folder, iso3 in COUNTRIES.items():
        path = DATA / folder / 'crime.csv'
        if not path.exists():
            continue
        with open(path, encoding='utf-8', newline='') as file:
            rows += [CrimeYear(country_id=iso3, state_id=row['state'] or None, year=int(row['year']), crime=row['crime'],
                               measure=row['measure'], value=float(row['value']))
                     for row in csv.DictReader(file)]
    return replace_rows(CrimeYear, rows, SOURCE)
