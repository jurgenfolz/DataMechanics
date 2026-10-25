"""Data Mechanics' own curated tables: compiled by hand from public sources, kept as CSV files in data/.

Each row of a file names its source. Add a country by adding its folder to data/politics/ and to COUNTRIES.
World War II's files are in data/ww2/.
"""

import csv
from datetime import date
from pathlib import Path

from django.conf import settings

DATA = Path(settings.BASE_DIR) / 'data' / 'politics'
WW2 = Path(settings.BASE_DIR) / 'data' / 'ww2'

# Folder in data/politics/ -> country code in geo_country.
COUNTRIES = {
    'brazil': 'BRA',
    'united-states': 'USA',
    'germany': 'DEU',
    'france': 'FRA',
    'austria': 'AUT',
}


def ww2_rows(name):
    """The rows of data/ww2/<name>, as dicts keyed by the header."""
    with open(WW2 / name, encoding='utf-8', newline='') as file:
        return list(csv.DictReader(file))


def optional_date(text):
    return date.fromisoformat(text) if text else None
