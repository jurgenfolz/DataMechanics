"""Reads Our World in Data charts ("grapher"): one CSV of data and one JSON of metadata per chart."""

import csv
import io

from providers import http
from providers.load import Source, replace_table

_CSV = 'https://ourworldindata.org/grapher/{slug}.csv?v=1&csvType=full&useColumnShortNames=true'
_METADATA = 'https://ourworldindata.org/grapher/{slug}.metadata.json?v=1&csvType=full&useColumnShortNames=true'
_PAGE = 'https://ourworldindata.org/grapher/{slug}'


def read_chart(slug, columns, rows=None):
    """Add one chart's values to rows: {(code, year): {field: value}}. columns maps CSV column -> table field.

    Rows without a code are regions OWID defines itself (e.g. "Asia") and are skipped.
    """
    rows = {} if rows is None else rows
    for record in csv.DictReader(io.StringIO(http.get_text(_CSV.format(slug=slug)))):
        if not record['code']:
            continue
        for column, field in columns.items():
            if record.get(column):
                rows.setdefault((record['code'], int(record['year'])), {})[field] = float(record[column])
    return rows


def source(slug):
    """The chart's citation and update date, from its metadata."""
    columns = http.get_json(_METADATA.format(slug=slug))['columns']
    meta = next(c for c in columns.values() if c.get('titleShort') != 'World region according to OWID')
    return Source(name=meta['citationShort'], url=_PAGE.format(slug=slug), updated=meta.get('lastUpdated') or '')


def load_charts(model, charts):
    """Load one or more charts into one table. charts maps slug -> {CSV column: table field}.

    Every field of the table appears in every row (None where a chart has no value); the first chart names the source.
    """
    rows = {}
    for slug, columns in charts.items():
        read_chart(slug, columns, rows)
    fields = [field for columns in charts.values() for field in columns.values()]
    rows = {key: {field: values.get(field) for field in fields} for key, values in rows.items()}
    return replace_table(model, rows, source(next(iter(charts))))
