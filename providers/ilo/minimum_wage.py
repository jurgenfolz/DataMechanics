"""Statutory monthly minimum wage, ILOSTAT dataflow DF_EAR_INEE_CUR_NB. Writes geo_minimum_wage_country_year.

The dataflow gives each wage in local currency, US dollars and PPP dollars; only the two comparable currencies are loaded.
Its rows are yearly, keyed by ISO alpha-3 codes, with no aggregates.
"""

import csv
import io
import re

from geo.models import MinimumWageCountryYear
from providers import http
from providers.load import Source, replace_table

_DATA = 'https://sdmx.ilo.org/rest/data/ILO,DF_EAR_INEE_CUR_NB/.A..CUR_TYPE_PPP+CUR_TYPE_USD?format=csv'
_DATAFLOW = 'https://sdmx.ilo.org/rest/dataflow/ILO/DF_EAR_INEE_CUR_NB?references=none&detail=full'
PAGE = 'https://ilostat.ilo.org/data/'
CURRENCIES = {'CUR_TYPE_PPP': 'ppp', 'CUR_TYPE_USD': 'usd'}


def run():
    rows = {}
    for row in csv.DictReader(io.StringIO(http.get_text(_DATA, encoding='utf-8-sig'))):
        if row['FREQ'] != 'A':
            continue
        values = rows.setdefault((row['REF_AREA'], int(row['TIME_PERIOD'])), dict.fromkeys(CURRENCIES.values()))
        values[CURRENCIES[row['CUR']]] = float(row['OBS_VALUE'])
    return replace_table(MinimumWageCountryYear, rows,
                         Source(name='ILOSTAT (ILO), Monthly minimum wage by currency', url=PAGE, updated=_last_update()))


def _last_update():
    """The dataflow's LAST_UPDATE annotation, titled "25/10/2026 08:30:52", as 2026-10-25."""
    match = re.search(r'<common:AnnotationTitle>(\d{2})/(\d{2})/(\d{4})[^<]*</common:AnnotationTitle>\s*'
                      r'<common:AnnotationType>LAST_UPDATE</common:AnnotationType>', http.get_text(_DATAFLOW))
    return f'{match.group(3)}-{match.group(2)}-{match.group(1)}' if match else ''
