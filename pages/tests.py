"""Languages: every page in English, German and Portuguese, with numbers and names written the local way."""

import re
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.utils import translation

from geo.models import Country, GdpPerCapitaCountryYear
from metrics import search
from metrics.catalog import CATEGORIES, CATEGORY_LABELS
from metrics.formatting import format_change, format_value


class LanguageTestCase(TestCase):
    """A request leaves its language active on the thread; English is restored so later tests are unaffected."""

    def tearDown(self):
        translation.activate(settings.LANGUAGE_CODE)


class LanguageTests(LanguageTestCase):
    def test_each_language_has_its_own_address(self):
        for path, lang, text in [('/', 'en', 'The world in numbers.'), ('/de/', 'de', 'Die Welt in Zahlen.'),
                                 ('/pt/', 'pt', 'O mundo em números.')]:
            response = self.client.get(path)
            self.assertContains(response, f'<html lang="{lang}">')
            self.assertContains(response, text)

    def test_switcher_keeps_the_page_and_its_query(self):
        response = self.client.get('/de/metrics/?q=gdp')
        self.assertContains(response, 'href="/metrics/?q=gdp" hreflang="en"')
        self.assertContains(response, 'href="/pt/metrics/?q=gdp" hreflang="pt"')
        self.assertContains(response, 'aria-current="true">DE</a>')

    def test_search_engines_see_every_language(self):
        response = self.client.get('/pt/politics/')
        for code, path in [('en', '/politics/'), ('de', '/de/politics/'), ('pt', '/pt/politics/'), ('x-default', '/politics/')]:
            self.assertContains(response, f'hreflang="{code}" href="http://testserver{path}"')

    def test_browser_strings_come_from_the_catalog(self):
        self.assertContains(self.client.get('/de/jsi18n/'), 'Ende der Amtszeit')
        self.assertContains(self.client.get('/pt/jsi18n/'), 'Fim do mandato')

    def test_old_wordpress_links_still_resolve_outside_the_prefixes(self):
        self.assertEqual(self.client.get('/no-such-post/').status_code, 404)

    def test_not_found_page_speaks_the_language_of_its_address(self):
        response = self.client.get('/pt/nada-aqui/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Esta página não existe.', status_code=404)


class LocalFormatTests(LanguageTestCase):
    def test_numbers_and_units(self):
        cases = {
            'en': ('$30.8 tn', '73.4 yrs', '1,234.5', '1.5%'),
            'de': ('$30,8 Bio.', '73,4 Jahre', '1.234,5', '1,5%'),
            'pt': ('US$ 30,8 tri', '73,4 anos', '1.234,5', '1,5%'),
        }
        for lang, (usd, years, points, change) in cases.items():
            with translation.override(lang):
                self.assertEqual(format_value(30_770_000_000_000, 'usd'), usd)
                self.assertEqual(format_value(73.4, 'years'), years)
                self.assertEqual(format_value(1234.5, 'points'), points)
                self.assertEqual(format_change(8.0, 6.5, 'percent'), change)

    def test_a_long_unit_is_dropped_only_when_compact(self):
        with translation.override('de'):
            self.assertEqual(format_value(12.3, 'per_1000'), '12,3 pro 1.000')
            self.assertEqual(format_value(12.3, 'per_1000', compact=True), '12,3')
            self.assertEqual(format_value(73.4, 'years', compact=True), '73,4 Jahre')

    def test_country_names(self):
        germany = Country.objects.create(iso3='DEU', iso2='de', name='Germany', name_de='Deutschland', name_pt='Alemanha')
        GdpPerCapitaCountryYear.objects.create(country=germany, year=2024, value=55_000)
        for path, name in [('/metrics/gdp-per-capita/data.json', 'Germany'), ('/de/metrics/gdp-per-capita/data.json', 'Deutschland'),
                           ('/pt/metrics/gdp-per-capita/data.json', 'Alemanha')]:
            self.assertEqual(self.client.get(path).json()['countries']['DEU']['name'], name)


class TranslatedSearchTests(LanguageTestCase):
    def test_finds_metrics_by_words_in_the_language_and_in_english(self):
        with translation.override('de'):
            self.assertEqual(search.find('Lebenserwartung')[0].slug, 'life-expectancy')
            self.assertEqual(search.find('life expectancy')[0].slug, 'life-expectancy')
        with translation.override('pt'):
            self.assertEqual(search.find('desemprego')[0].slug, 'unemployment')


class CatalogTests(TestCase):
    def test_every_category_has_a_label(self):
        self.assertLessEqual(set(CATEGORIES), set(CATEGORY_LABELS))

    def test_every_string_is_translated(self):
        """No empty or fuzzy entry in locale/: run makemessages, then translate what it adds."""
        for po in Path(settings.BASE_DIR, 'locale').glob('*/LC_MESSAGES/*.po'):
            text = po.read_text(encoding='utf-8')
            self.assertNotIn('#, fuzzy\nmsgid "', text.split('\n\n', 1)[1], po)
            entries = text.split('\n\n')[1:]
            for entry in entries:
                if entry.startswith('#~'):
                    continue
                strings = re.findall(r'^msgstr(?:\[\d\])? ((?:".*"\n?)+)', entry + '\n', re.M)
                self.assertTrue(strings and all(s.strip() != '""' for s in strings), f'{po}: {entry[:120]}')
