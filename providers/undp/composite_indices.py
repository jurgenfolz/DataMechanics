"""Reads the UNDP Human Development Report composite indices file, shared by hdi.py and schooling.py.

The file is wide: one row per country, one column per indicator and year, e.g. hdi_1990 ... hdi_2023.
"""

import csv
import io
import re

from providers import http
from providers.load import Source

REPORT = 'HDR25'
URL = f'https://hdr.undp.org/sites/default/files/2025_HDR/{REPORT}_Composite_indices_complete_time_series.csv'
PAGE = 'https://hdr.undp.org/data-center/documentation-and-downloads'
SOURCE = Source(name='UNDP, Human Development Report 2025', url=PAGE, updated=REPORT)


def read_columns(prefixes):
    """Long rows for the given column prefixes: {(iso3, year): {prefix: value}}.

    read_columns(['mys', 'eys']) reads mys_1990 ... and eys_1990 ... into {'mys': ..., 'eys': ...}.
    """
    text = http.get_text(URL, encoding='latin-1')
    pattern = re.compile(rf'^({"|".join(prefixes)})_(\d{{4}})$')
    rows = {}
    for record in csv.DictReader(io.StringIO(text)):
        for column, raw in record.items():
            match = pattern.match(column or '')
            if not match or not raw.strip():
                continue
            prefix, year = match.group(1), int(match.group(2))
            rows.setdefault((record['iso3'], year), dict.fromkeys(prefixes))[prefix] = float(raw)
    return rows
