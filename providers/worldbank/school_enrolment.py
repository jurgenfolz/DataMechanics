"""Gross enrolment in secondary and tertiary education, UNESCO Institute for Statistics via the World Bank. Writes geo_school_enrolment_country_year."""

from geo.models import SchoolEnrolmentCountryYear

from . import api

COLUMNS = {
    'SE.SEC.ENRR': 'secondary',
    'SE.TER.ENRR': 'tertiary',
}


def run():
    return api.load_indicators(SchoolEnrolmentCountryYear, COLUMNS)
