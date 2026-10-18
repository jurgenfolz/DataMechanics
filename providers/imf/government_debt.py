"""General government gross debt (% of GDP), IMF World Economic Outlook. Writes geo_government_debt_country_year.

The IMF DataMapper API serves the WEO series GGXWDG_NGDP, forecasts included.
Only years before the current one are kept: the WEO marks the current year onward as projections.
"""

from datetime import date

from geo.models import GovernmentDebtCountryYear
from providers import http
from providers.load import Source, replace_table

CODE = 'GGXWDG_NGDP'
API = f'https://www.imf.org/external/datamapper/api/v1/{CODE}'
INDICATORS_API = 'https://www.imf.org/external/datamapper/api/v1/indicators'
PAGE = f'https://www.imf.org/external/datamapper/{CODE}@WEO'


def run():
    by_country = http.get_json(API)['values'][CODE]
    release = http.get_json(INDICATORS_API)['indicators'][CODE]['source']  # e.g. "World Economic Outlook (October 2026)"
    first_projected_year = date.today().year

    rows = {
        (code, int(year)): {'value': value}
        for code, years in by_country.items()
        for year, value in years.items()
        if value is not None and int(year) < first_projected_year
    }
    return replace_table(GovernmentDebtCountryYear, rows, Source(name=f'IMF, {release}', url=PAGE, updated=release))
