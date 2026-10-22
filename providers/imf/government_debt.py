"""General government gross debt (% of GDP), IMF World Economic Outlook series GGXWDG_NGDP.
Writes geo_government_debt_country_year.
"""

from geo.models import GovernmentDebtCountryYear

from . import datamapper


def run():
    return datamapper.load_series(GovernmentDebtCountryYear, 'GGXWDG_NGDP', 'WEO')
