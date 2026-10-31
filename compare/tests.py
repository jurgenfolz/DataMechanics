import json
import re

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from metrics.catalog import BY_SLUG, METRICS
from metrics.tests import load_sample

from . import views


def page_config(response):
    """The JSON the page hands its script (compare-config)."""
    match = re.search(r'<script id="compare-config" type="application/json">(.*?)</script>', response.content.decode(), re.S)
    return json.loads(match.group(1))


class CompareTests(TestCase):
    def setUp(self):
        load_sample()

    def tearDown(self):
        translation.activate(settings.LANGUAGE_CODE)

    def test_every_measure_is_offered_once(self):
        keys = [option['key'] for group in views._groups() for option in group['options']]
        self.assertEqual(len(keys), sum(len(metric.series) for metric in METRICS))
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn('gdp-per-capita:ppp', keys)
        self.assertIn('life-expectancy', keys)

    def test_defaults_are_offered(self):
        keys = {option['key'] for group in views._groups() for option in group['options']}
        self.assertLessEqual({views.DEFAULT_LEFT, views.DEFAULT_RIGHT}, keys)

    def test_page_names_each_metric_with_its_source(self):
        response = self.client.get(reverse('compare:index'))
        self.assertContains(response, '<option value="gdp-per-capita:ppp">GDP per capita · PPP</option>', html=True)
        about = page_config(response)['metrics']['gdp-per-capita']
        self.assertEqual(about['dataUrl'], reverse('metrics:data', args=['gdp-per-capita']))
        self.assertIn('World Bank, World Development Indicators', about['source'])
        self.assertIn('Source: not loaded yet.', page_config(response)['metrics']['life-expectancy']['source'])

    def test_every_language_has_the_page(self):
        for path, title in [('/compare/', 'Compare metrics'), ('/de/compare/', 'Kennzahlen vergleichen'),
                            ('/pt/compare/', 'Comparar indicadores')]:
            self.assertContains(self.client.get(path), f'<h1>{title}</h1>', html=True)

    def test_metric_pages_link_here(self):
        response = self.client.get(reverse('metrics:detail', args=['unemployment']))
        self.assertContains(response, f'href="{reverse("compare:index")}?left=unemployment"')

    def test_data_names_what_values_are_in(self):
        metric = BY_SLUG['gdp-per-capita']
        response = self.client.get(reverse('metrics:data', args=[metric.slug]))
        self.assertEqual(response.json()['measuredIn'], 'current US$')
