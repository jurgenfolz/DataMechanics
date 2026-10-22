"""Reads one series from the IMF DataMapper API, which serves the World Economic Outlook, the Fiscal Monitor and more.

The series come with the IMF's forecasts. Only years before the current one are kept: the IMF marks the current year onward as projections.
"""

from datetime import date

from providers import http
from providers.load import Source, replace_table

API = 'https://www.imf.org/external/datamapper/api/v1/{code}'
INDICATORS_API = 'https://www.imf.org/external/datamapper/api/v1/indicators'
PAGE = 'https://www.imf.org/external/datamapper/{code}@{dataset}'


def load_series(model, code, dataset):
    """Replace the table of `model` with the IMF series `code` from `dataset` (WEO, FM, ...), in its `value` column."""
    by_country = http.get_json(API.format(code=code))['values'][code]
    release = http.get_json(INDICATORS_API)['indicators'][code]['source']  # e.g. "World Economic Outlook (October 2026)"
    first_projected_year = date.today().year
    rows = {
        (country, int(year)): {'value': value}
        for country, years in by_country.items()
        for year, value in years.items()
        if value is not None and int(year) < first_projected_year
    }
    return replace_table(model, rows, Source(name=f'IMF, {release}', url=PAGE.format(code=code, dataset=dataset), updated=release))
