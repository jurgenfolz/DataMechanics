import json
import re

from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from .catalog import BY_SLUG, EVENTS, KINDS


class CatalogTests(TestCase):
    def test_slugs_are_unique_and_events_dated(self):
        self.assertEqual(len(BY_SLUG), len(EVENTS))
        self.assertEqual([e.date for e in EVENTS], sorted(e.date for e in EVENTS))
        for event in EVENTS:
            self.assertIn(event.kind, KINDS, event.slug)
            self.assertTrue(event.wiki.startswith('https://en.wikipedia.org/wiki/'), event.slug)
            if event.end:
                self.assertGreater(event.end, event.date, event.slug)
                self.assertFalse(event.ongoing, event.slug)

    def test_titles_stay_short(self):
        # A title sits on the chart in a small chip.
        for event in EVENTS:
            self.assertLessEqual(len(str(event.title)), 36, event.slug)


class JsonTests(TestCase):
    def test_events_in_the_pages_language(self):
        response = self.client.get(reverse('events:json'))
        self.assertEqual(response['Cache-Control'], 'public, max-age=3600')
        events = response.json()['events']
        self.assertEqual(events[0]['slug'], 'ww2-ends')
        self.assertEqual(events[0]['kindLabel'], 'Treaties and unions')
        with translation.override('de'):
            german = self.client.get('/de/events.json').json()['events']
        self.assertEqual(german[0]['slug'], 'ww2-ends')
        self.assertNotEqual(german[0]['title'], events[0]['title'])


class PageTests(TestCase):
    def setUp(self):
        from metrics.tests import load_sample
        load_sample()

    def test_the_charts_offer_the_picker(self):
        for url, script in ((reverse('metrics:detail', args=['gdp-per-capita']), 'metric-config'), (reverse('compare:index'), 'compare-config')):
            response = self.client.get(url)
            self.assertContains(response, 'data-events-picker')
            self.assertContains(response, 'data-event-keys')
            config = json.loads(re.search(rf'<script id="{script}" type="application/json">(.*?)</script>', response.content.decode(), re.S).group(1))
            self.assertEqual(config['eventsUrl'], reverse('events:json'))
