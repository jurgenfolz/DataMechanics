"""General government net lending or borrowing (% of GDP), IMF World Economic Outlook series GGXCNL_NGDP.
Writes geo_budget_balance_country_year.
"""

from geo.models import BudgetBalanceCountryYear

from . import datamapper


def run():
    return datamapper.load_series(BudgetBalanceCountryYear, 'GGXCNL_NGDP', 'WEO')
