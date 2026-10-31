"""Life expectancy at birth since the 1800s (Riley, Zijdeman, HMD, UN WPP) and by sex since 1950 (UN WPP), via Our World in Data. Writes geo_life_expectancy_country_year."""

from geo.models import LifeExpectancyCountryYear

from . import grapher

CHARTS = {
    'life-expectancy': {'life_expectancy_0': 'value'},
    'life-expectancy-of-women-vs-life-expectancy-of-men': {'life_expectancy__sex_female__age_0__variant_estimates': 'women', 'life_expectancy__sex_male__age_0__variant_estimates': 'men'},
}


def run():
    return grapher.load_charts(LifeExpectancyCountryYear, CHARTS)
