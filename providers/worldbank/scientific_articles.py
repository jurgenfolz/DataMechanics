"""Scientific and technical journal articles (NSF), World Bank indicator IP.JRN.ARTC.SC. Writes geo_scientific_articles_country_year."""

from geo.models import ScientificArticlesCountryYear

from . import api

CODE = 'IP.JRN.ARTC.SC'


def run():
    return api.load_indicator(ScientificArticlesCountryYear, CODE)
