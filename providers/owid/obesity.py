"""Adult obesity (BMI of 30 or more, age-standardised), WHO via Our World in Data. Writes geo_obesity_country_year.

WHO licenses this data under CC BY-NC-SA 4.0: non-commercial use, and copies keep the same licence.
"""

from geo.models import ObesityCountryYear

from . import grapher

CHARTS = {
    'obesity-prevalence-adults-who-gho': {
        'obesity_among_adults__bmi__gt__30_kg_m2__age_standardized_estimate__pct__sex_both_sexes__age_group_18plus__years_of_age': 'value',
    },
}


def run():
    return grapher.load_charts(ObesityCountryYear, CHARTS)
