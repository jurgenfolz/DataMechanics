"""Government spending on education as a share of GDP (UNESCO and historical records), as compiled by Our World in Data. Writes geo_education_spending_country_year."""

from geo.models import EducationSpendingCountryYear

from . import grapher

CHARTS = {'education-spending': {'combined_expenditure_share_gdp': 'value'}}


def run():
    return grapher.load_charts(EducationSpendingCountryYear, CHARTS)
