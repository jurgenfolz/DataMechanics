"""Annual working hours per worker, Penn World Table via Our World in Data. Writes geo_working_hours_country_year.

The chart reaches back to 1870 with Huberman and Minns's estimates, which carry no open licence; only the Penn World Table's years, from 1950, are loaded.
"""

from geo.models import WorkingHoursCountryYear
from providers.load import replace_table

from . import grapher

CHART = 'annual-working-hours-per-worker'
COLUMNS = {'working_hours_omm': 'value'}
FIRST_YEAR = 1950


def run():
    rows = {key: fields for key, fields in grapher.read_chart(CHART, COLUMNS).items() if key[1] >= FIRST_YEAR}
    return replace_table(WorkingHoursCountryYear, rows, grapher.source(CHART, next(iter(COLUMNS))))
