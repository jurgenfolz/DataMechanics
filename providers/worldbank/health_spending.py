"""Current health expenditure per person, current US$ (WHO), World Bank indicator SH.XPD.CHEX.PC.CD. Writes geo_health_spending_country_year."""

from geo.models import HealthSpendingCountryYear

from . import api

CODE = 'SH.XPD.CHEX.PC.CD'


def run():
    return api.load_indicator(HealthSpendingCountryYear, CODE)
