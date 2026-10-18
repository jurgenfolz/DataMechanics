"""World Bank Indicators API (https://datahelpdesk.worldbank.org/knowledgebase/topics/125589)."""

from providers import http
from providers.load import Source, replace_table

_API = 'https://api.worldbank.org/v2/country/all/indicator/{code}?format=json&per_page=30000&source=2'
_PAGE = 'https://data.worldbank.org/indicator/{code}'
SOURCE_NAME = 'World Bank, World Development Indicators'


def fetch_indicator(code):
    """Every yearly value of one indicator, for all countries and aggregates.

    Returns ({(iso3, year): value}, the date the World Bank last updated the indicator).
    """
    meta, rows = http.get_json(_API.format(code=code))
    if meta['pages'] > 1:
        raise ValueError(f'{code} has more than one page of results; raise per_page.')
    values = {
        (row['countryiso3code'], int(row['date'])): row['value']
        for row in rows
        if row['value'] is not None and row['countryiso3code']
    }
    return values, meta['lastupdated']


def source(code, updated):
    return Source(name=SOURCE_NAME, url=_PAGE.format(code=code), updated=updated)


def load_indicator(model, code):
    """Load one indicator into a fact table whose only measure is `value`."""
    return load_indicators(model, {code: 'value'})


def load_indicators(model, columns):
    """Load several indicators into one fact table. columns maps indicator code -> table column.

    The first indicator names the source link.
    """
    rows, updated = {}, ''
    for code, column in columns.items():
        values, updated = fetch_indicator(code)
        for key, value in values.items():
            rows.setdefault(key, dict.fromkeys(columns.values()))[column] = value
    return replace_table(model, rows, source(next(iter(columns)), updated))
