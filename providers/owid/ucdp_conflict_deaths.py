"""Deaths in armed conflicts by the country they happened in, UCDP via Our World in Data. Writes geo_conflict_deaths_country_year.

The chart's current year is a part of a year, so it is left out.
"""

from datetime import date

from geo.models import ConflictDeathsCountryYear
from providers.load import replace_table

from . import grapher

CHART = 'deaths-in-armed-conflicts-by-country'
COLUMNS = {'number_deaths_ongoing_conflicts__conflict_type_all': 'value'}


def run():
    rows = {key: fields for key, fields in grapher.read_chart(CHART, COLUMNS).items() if key[1] < date.today().year}
    return replace_table(ConflictDeathsCountryYear, rows, grapher.source(CHART, next(iter(COLUMNS))))
