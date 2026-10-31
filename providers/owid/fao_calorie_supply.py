"""Daily food supply per person in kilocalories, FAO and historical sources via Our World in Data. Writes geo_calorie_supply_country_year."""

from geo.models import CalorieSupplyCountryYear

from . import grapher

CHARTS = {
    'daily-per-capita-caloric-supply': {'daily_calories': 'value'},
}


def run():
    return grapher.load_charts(CalorieSupplyCountryYear, CHARTS)
