"""Reads Our World in Data charts ("grapher"): one CSV of data and one JSON of metadata per chart."""

import csv
import io

from providers import http
from providers.load import Source, replace_table

_CSV = 'https://ourworldindata.org/grapher/{slug}.csv?v=1&csvType=full&useColumnShortNames=true{view}'
_METADATA = 'https://ourworldindata.org/grapher/{slug}.metadata.json?v=1&csvType=full&useColumnShortNames=true{view}'
_PAGE = 'https://ourworldindata.org/grapher/{slug}{view}'

# Some charts show several views, picked by options in their address, e.g. 'quantile=richest_1pct&welfare_type=before_tax'.
# A module passes them as `view`; the CSV, the metadata and the source link then all show that view.


def read_chart(slug, columns, rows=None, view=''):
    """Add one chart's values to rows: {(code, year): {field: value}}. columns maps CSV column -> table field.

    Rows without a code are regions OWID defines itself (e.g. "Asia") and are skipped.
    """
    rows = {} if rows is None else rows
    for record in csv.DictReader(io.StringIO(http.get_text(_CSV.format(slug=slug, view=f'&{view}' if view else '')))):
        if not record['code']:
            continue
        for column, field in columns.items():
            if record.get(column):
                rows.setdefault((record['code'], int(record['year'])), {})[field] = float(record[column])
    return rows


def source(slug, column, view=''):
    """The citation and update date of one of the chart's columns, from its metadata."""
    columns = http.get_json(_METADATA.format(slug=slug, view=f'&{view}' if view else ''))['columns']
    meta = columns[column]
    return Source(name=meta['citationShort'], url=_PAGE.format(slug=slug, view=f'?{view}' if view else ''),
                  updated=meta.get('lastUpdated') or '')


def load_charts(model, charts, view='', scale=None):
    """Load one or more charts into one table. charts maps slug -> {CSV column: table field}.

    Every field of the table appears in every row (None where a chart has no value).
    The first chart's first column names the source. `scale` maps a field to a factor its values are multiplied by.
    """
    rows = {}
    for slug, columns in charts.items():
        read_chart(slug, columns, rows, view)
    fields = [field for columns in charts.values() for field in columns.values()]
    factor = scale or {}
    rows = {key: {field: None if values.get(field) is None else values[field] * factor.get(field, 1) for field in fields}
            for key, values in rows.items()}
    slug, columns = next(iter(charts.items()))
    return replace_table(model, rows, source(slug, next(iter(columns)), view))
