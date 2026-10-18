"""The five V-Dem democracy indices, as published by Our World in Data. Writes geo_democracy_country_year.

V-Dem (Varieties of Democracy) produces the indices. Our World in Data republishes them as one chart each.
"""

import csv
import io

from geo.models import DemocracyCountryYear
from providers import http
from providers.load import Source, replace_table

_CSV = 'https://ourworldindata.org/grapher/{slug}.csv?v=1&csvType=full&useColumnShortNames=true'
_METADATA = 'https://ourworldindata.org/grapher/{slug}.metadata.json?v=1&csvType=full&useColumnShortNames=true'

# Column in geo_democracy_country_year -> Our World in Data chart.
CHARTS = {
    'electoral': 'electoral-democracy-index',
    'liberal': 'liberal-democracy-index',
    'participatory': 'participatory-democracy-index',
    'deliberative': 'deliberative-democracy-index-vdem',
    'egalitarian': 'egalitarian-democracy-index-vdem',
}
PAGE = 'https://ourworldindata.org/grapher/electoral-democracy-index'


def run():
    rows = {}
    for column, slug in CHARTS.items():
        for record in csv.DictReader(io.StringIO(http.get_text(_CSV.format(slug=slug)))):
            if not record['code']:
                continue  # regions without a code, e.g. "Asia"
            # The value column has a chart-specific name, e.g. electdem_vdem__estimate_best.
            value = next(v for k, v in record.items() if k.endswith('__estimate_best'))
            if value:
                rows.setdefault((record['code'], int(record['year'])), dict.fromkeys(CHARTS))[column] = float(value)

    meta = next(iter(http.get_json(_METADATA.format(slug=CHARTS['electoral']))['columns'].values()))
    source = Source(name=meta['citationShort'], url=PAGE, updated=meta['lastUpdated'])
    return replace_table(DemocracyCountryYear, rows, source)
