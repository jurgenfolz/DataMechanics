"""Data Mechanics' own curated tables: compiled by hand from public sources, kept as CSV files in data/.

Each row of a file names its source. Add a country by adding its folder to data/politics/ and to COUNTRIES.
"""

from pathlib import Path

from django.conf import settings

DATA = Path(settings.BASE_DIR) / 'data' / 'politics'

# Folder in data/politics/ -> country code in geo_country.
COUNTRIES = {
    'brazil': 'BRA',
    'united-states': 'USA',
    'germany': 'DEU',
    'france': 'FRA',
    'austria': 'AUT',
}
