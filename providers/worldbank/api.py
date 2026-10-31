"""World Bank Indicators API (https://datahelpdesk.worldbank.org/knowledgebase/topics/125589)."""

from providers import http
from providers.load import Source, replace_table

_API = 'https://api.worldbank.org/v2/country/all/indicator/{code}?format=json&per_page=30000&source={source}'
# Each database's name and the page an indicator links to.
WDI = 2
WGI = 3
DATABASES = {
    WDI: ('World Bank, World Development Indicators', 'https://data.worldbank.org/indicator/{code}'),
    WGI: ('World Bank, Worldwide Governance Indicators', 'https://www.worldbank.org/en/publication/worldwide-governance-indicators'),
}
SOURCE_NAME = DATABASES[WDI][0]


def fetch_indicator(code, database=WDI):
    """Every yearly value of one indicator, for all countries and aggregates.

    Returns ({(iso3, year): value}, the date the World Bank last updated the indicator).
    `database` is the World Bank database the indicator lives in: WDI unless said otherwise.
    """
    meta, rows = http.get_json(_API.format(code=code, source=database))
    if meta['pages'] > 1:
        raise ValueError(f'{code} has more than one page of results; raise per_page.')
    values = {
        (row['countryiso3code'], int(row['date'])): row['value']
        for row in rows
        if row['value'] is not None and row['countryiso3code']
    }
    return values, meta['lastupdated']


def source(code, updated, database=WDI):
    name, page = DATABASES[database]
    return Source(name=name, url=page.format(code=code), updated=updated)


def load_indicator(model, code):
    """Load one indicator into a fact table whose only measure is `value`."""
    return load_indicators(model, {code: 'value'})


def without_rounded(values, amounts, database=WDI):
    """Drop the shares of GDP whose amount the World Bank rounded away.

    `amounts` are the indicators of the amount a share divides by GDP, in local currency; several are summed (exports and imports for trade).
    Some countries' amounts are stored rounded to whole units of today's currency.
    Where the currency lost many zeros, as Brazil's did before the real, one unit is a large part of the economy.
    Brazil's farms then made 0 reais in 1960, and 1 real in 1981: 0% and 11% of GDP.
    Below 100 units the rounding alone can move a share by more than half a percent, so the share is dropped.
    Decimal amounts were not rounded and stay, however small.
    """
    totals = {}
    for code in amounts:
        for key, amount in fetch_indicator(code, database)[0].items():
            totals[key] = totals.get(key, 0) + amount
    return {
        key: value for key, value in values.items()
        if key not in totals or abs(totals[key]) >= 100 or not float(totals[key]).is_integer()
    }


def load_indicators(model, columns, database=WDI, scale=None, amounts=None):
    """Load several indicators into one fact table. columns maps indicator code -> table column.

    The first indicator names the source link. `scale` maps a column to a factor its values are multiplied by.
    `amounts` maps a share's indicator to the indicators of its amount in local currency (see `without_rounded`).
    """
    rows, updated = {}, ''
    for code, column in columns.items():
        values, updated = fetch_indicator(code, database)
        if code in (amounts or {}):
            values = without_rounded(values, amounts[code], database)
        factor = (scale or {}).get(column, 1)
        for key, value in values.items():
            rows.setdefault(key, dict.fromkeys(columns.values()))[column] = value * factor
    return replace_table(model, rows, source(next(iter(columns)), updated, database))
